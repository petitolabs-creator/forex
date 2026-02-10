package forex.services.cache

import cats.effect.{ ContextShift, IO, Timer }
import forex.domain.{ Currency, Price, Rate, Timestamp }
import forex.services.valkey.ValkeyClient
import fs2.Stream
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.should.Matchers

import scala.concurrent.ExecutionContext
import scala.concurrent.duration._

class RatesCacheSpec extends AnyFreeSpec with Matchers {

  implicit val cs: ContextShift[IO] = IO.contextShift(ExecutionContext.global)
  implicit val timer: Timer[IO] = IO.timer(ExecutionContext.global)

  def mockValkey(get: IO[Option[List[Rate]]], set: List[Rate] => IO[Unit] = _ => IO.unit): ValkeyClient[IO] =
    new ValkeyClient[IO] {
      def getRates(): IO[Option[List[Rate]]] = get
      def setRates(rates: List[Rate]): IO[Unit] = set(rates)
      def publishRatesUpdated(): IO[Unit] = IO.unit
    }

  "RatesCache" - {
    "should start with empty cache" in {
      val mock = mockValkey(IO.pure(None))
      val syncTrigger = Stream.never[IO] // no events
      val (cache, _) = RatesCache.make[IO](mock, syncTrigger).unsafeRunSync()
      cache.getRates().unsafeRunSync() shouldBe None
    }

    "should update and retrieve rates" in {
      val mock = mockValkey(IO.pure(None))
      val syncTrigger = Stream.never[IO]
      val testRates = List(
        Rate(
          Rate.Pair(Currency.USD, Currency.EUR),
          Price(0.85),
          Timestamp.now
        )
      )
      val (cache, _) = RatesCache.make[IO](mock, syncTrigger).unsafeRunSync()
      cache.updateRates(testRates).unsafeRunSync()
      cache.getRates().unsafeRunSync() shouldBe Some(testRates)
    }

    "should sync from Valkey on initialization" in {
      val testRates = List(
        Rate(
          Rate.Pair(Currency.USD, Currency.JPY),
          Price(110.5),
          Timestamp.now
        )
      )
      val mock = mockValkey(IO.pure(Some(testRates)))
      val syncTrigger = Stream.never[IO]
      val (cache, syncJob) = RatesCache.make[IO](mock, syncTrigger).unsafeRunSync()
      val rates = (for {
        _ <- syncJob.start
        _ <- IO.sleep(300.millis)
        r <- cache.getRates()
      } yield r).unsafeRunSync()
      rates shouldBe Some(testRates)
    }
  }
}
