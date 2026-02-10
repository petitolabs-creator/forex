package forex.services.rates

import cats.effect.IO
import forex.domain.{ Currency, Price, Rate, Timestamp }
import forex.services.oneframe.OneFrameClient
import forex.services.oneframe.errors.{ Error => OneFrameError }
import forex.services.rates.errors.{ Error => RatesError }
import forex.services.rates.interpreters.OneFrameLive
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.should.Matchers

import java.time.OffsetDateTime

class OneFrameLiveSpec extends AnyFreeSpec with Matchers {

  "OneFrameLive" - {

    "get" - {
      "should return rate for valid pair" in {
        val mockRates = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.now())
          ),
          Rate(
            pair = Rate.Pair(Currency.EUR, Currency.USD),
            price = Price(BigDecimal("1.17")),
            timestamp = Timestamp(OffsetDateTime.now())
          )
        )

        val mockClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(mockRates))
        }

        val interpreter = new OneFrameLive[IO](mockClient)
        val pair = Rate.Pair(Currency.USD, Currency.EUR)

        val result = interpreter.get(pair).unsafeRunSync()

        result.isRight shouldBe true
        result.toOption.get.pair shouldBe pair
        result.toOption.get.price shouldBe Price(BigDecimal("0.85"))
      }

      "should return error when pair not found" in {
        val mockRates = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.now())
          )
        )

        val mockClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(mockRates))
        }

        val interpreter = new OneFrameLive[IO](mockClient)
        val pair = Rate.Pair(Currency.JPY, Currency.GBP) // Not in mock data

        val result = interpreter.get(pair).unsafeRunSync()

        result.isLeft shouldBe true
        result.left.toOption.get shouldBe a[RatesError.RateLookupFailed]
      }

      "should propagate OneFrame client errors" in {
        val mockClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Left(OneFrameError.OneFrameLookupFailed("API error")))
        }

        val interpreter = new OneFrameLive[IO](mockClient)
        val pair = Rate.Pair(Currency.USD, Currency.EUR)

        val result = interpreter.get(pair).unsafeRunSync()

        result.isLeft shouldBe true
        result.left.toOption.get shouldBe a[RatesError.RateLookupFailed]
      }

      "should handle empty rate list" in {
        val mockClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(List.empty))
        }

        val interpreter = new OneFrameLive[IO](mockClient)
        val pair = Rate.Pair(Currency.USD, Currency.EUR)

        val result = interpreter.get(pair).unsafeRunSync()

        result.isLeft shouldBe true
        result.left.toOption.get shouldBe a[RatesError.RateLookupFailed]
      }

      "should handle multiple rates and find correct one" in {
        val mockRates = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.now())
          ),
          Rate(
            pair = Rate.Pair(Currency.JPY, Currency.GBP),
            price = Price(BigDecimal("0.45")),
            timestamp = Timestamp(OffsetDateTime.now())
          ),
          Rate(
            pair = Rate.Pair(Currency.EUR, Currency.USD),
            price = Price(BigDecimal("1.17")),
            timestamp = Timestamp(OffsetDateTime.now())
          )
        )

        val mockClient = new OneFrameClient[IO] {
          override def getAllRates(): IO[OneFrameError Either List[Rate]] =
            IO.pure(Right(mockRates))
        }

        val interpreter = new OneFrameLive[IO](mockClient)
        val pair = Rate.Pair(Currency.JPY, Currency.GBP)

        val result = interpreter.get(pair).unsafeRunSync()

        result.isRight shouldBe true
        result.toOption.get.pair shouldBe pair
        result.toOption.get.price shouldBe Price(BigDecimal("0.45"))
      }
    }
  }
}
