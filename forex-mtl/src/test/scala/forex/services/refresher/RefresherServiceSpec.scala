package forex.services.refresher

import cats.effect.IO
import forex.domain.{ Currency, Price, Rate, Timestamp }
import forex.services.oneframe.OneFrameClient
import forex.services.oneframe.errors.{ Error => OneFrameError }
import forex.services.valkey.ValkeyClient
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.should.Matchers

import java.time.OffsetDateTime

class RefresherServiceSpec extends AnyFreeSpec with Matchers {

  "RefresherService" - {

    "refresh" - {
      "should fetch from One-Frame and write to Valkey on success" in {
        val mockRates = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.now())
          ),
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.JPY),
            price = Price(BigDecimal("110.25")),
            timestamp = Timestamp(OffsetDateTime.now())
          )
        )

        var valkeyWrites: List[List[Rate]] = List.empty

        val mockOneFrameClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(mockRates))
        }

        val mockValkeyClient = new ValkeyClient[IO] {
          override def getRates(): IO[Option[List[Rate]]] =
            IO.pure(None)
          override def setRates(rates: List[Rate]): IO[Unit] =
            IO.delay { valkeyWrites = valkeyWrites :+ rates }
          override def publishRatesUpdated(): IO[Unit] = IO.unit
        }

        val refresher = RefresherService.make[IO](mockOneFrameClient, mockValkeyClient)
        val result = refresher.refresh().unsafeRunSync()

        result shouldBe Right(2)
        valkeyWrites should have size 1
        valkeyWrites.head shouldBe mockRates
      }

      "should return error when One-Frame API fails" in {
        val mockOneFrameClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Left(OneFrameError.OneFrameLookupFailed("API timeout")))
        }

        val mockValkeyClient = new ValkeyClient[IO] {
          override def getRates(): IO[Option[List[Rate]]] =
            IO.pure(None)
          override def setRates(rates: List[Rate]): IO[Unit] =
            IO.pure(())
          override def publishRatesUpdated(): IO[Unit] = IO.unit
        }

        val refresher = RefresherService.make[IO](mockOneFrameClient, mockValkeyClient)
        val result = refresher.refresh().unsafeRunSync()

        result.isLeft shouldBe true
        result.left.toOption.get should include("One-Frame API error")
      }

      "should not write to Valkey when One-Frame fails" in {
        var valkeyWriteCount = 0

        val mockOneFrameClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Left(OneFrameError.OneFrameLookupFailed("API error")))
        }

        val mockValkeyClient = new ValkeyClient[IO] {
          override def getRates(): IO[Option[List[Rate]]] =
            IO.pure(None)
          override def setRates(rates: List[Rate]): IO[Unit] =
            IO.delay { valkeyWriteCount += 1 }
          override def publishRatesUpdated(): IO[Unit] = IO.unit
        }

        val refresher = RefresherService.make[IO](mockOneFrameClient, mockValkeyClient)
        val result = refresher.refresh().unsafeRunSync()

        result.isLeft shouldBe true
        valkeyWriteCount shouldBe 0
      }

      "should handle Valkey write failures" in {
        val mockRates = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.now())
          )
        )

        val mockOneFrameClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(mockRates))
        }

        val mockValkeyClient = new ValkeyClient[IO] {
          override def getRates(): IO[Option[List[Rate]]] =
            IO.pure(None)
          override def setRates(rates: List[Rate]): IO[Unit] =
            IO.raiseError(new RuntimeException("Valkey connection failed"))
          override def publishRatesUpdated(): IO[Unit] = IO.unit
        }

        val refresher = RefresherService.make[IO](mockOneFrameClient, mockValkeyClient)
        val result = refresher.refresh().unsafeRunSync()

        result.isLeft shouldBe true
        result.left.toOption.get should include("Unexpected error")
      }

      "should return correct rate count on success" in {
        val mockRates = (1 to 72).map { i =>
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal(s"0.$i")),
            timestamp = Timestamp(OffsetDateTime.now())
          )
        }.toList

        val mockOneFrameClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(mockRates))
        }

        val mockValkeyClient = new ValkeyClient[IO] {
          override def getRates(): IO[Option[List[Rate]]] =
            IO.pure(None)
          override def setRates(rates: List[Rate]): IO[Unit] =
            IO.pure(())
          override def publishRatesUpdated(): IO[Unit] = IO.unit
        }

        val refresher = RefresherService.make[IO](mockOneFrameClient, mockValkeyClient)
        val result = refresher.refresh().unsafeRunSync()

        result shouldBe Right(72)
      }

      "should handle empty rate list from One-Frame" in {
        val mockOneFrameClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(List.empty))
        }

        var valkeyWrites: List[List[Rate]] = List.empty

        val mockValkeyClient = new ValkeyClient[IO] {
          override def getRates(): IO[Option[List[Rate]]] =
            IO.pure(None)
          override def setRates(rates: List[Rate]): IO[Unit] =
            IO.delay { valkeyWrites = valkeyWrites :+ rates }
          override def publishRatesUpdated(): IO[Unit] = IO.unit
        }

        val refresher = RefresherService.make[IO](mockOneFrameClient, mockValkeyClient)
        val result = refresher.refresh().unsafeRunSync()

        result shouldBe Right(0)
        valkeyWrites should have size 1
        valkeyWrites.head shouldBe List.empty
      }
    }
  }
}
