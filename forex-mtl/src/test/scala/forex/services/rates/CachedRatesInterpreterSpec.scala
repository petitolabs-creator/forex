package forex.services.rates

import cats.effect.IO
import forex.domain.{ Currency, Price, Rate, Timestamp }
import forex.services.cache.RatesCache
import forex.services.rates.interpreters.CachedRatesInterpreter
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.should.Matchers

class CachedRatesInterpreterSpec extends AnyFreeSpec with Matchers {

  val testTimestamp = Timestamp.now

  val mockRates = List(
    Rate(Rate.Pair(Currency.USD, Currency.EUR), Price(0.85), testTimestamp),
    Rate(Rate.Pair(Currency.USD, Currency.JPY), Price(110.5), testTimestamp),
    Rate(Rate.Pair(Currency.USD, Currency.GBP), Price(0.72), testTimestamp)
  )

  def mockCache(rates: Option[List[Rate]]): RatesCache[IO] = new RatesCache[IO] {
    def getRates(): IO[Option[List[Rate]]] = IO.pure(rates)
    def updateRates(rates: List[Rate]): IO[Unit] = IO.unit
  }

  "CachedRatesInterpreter" - {
    "should return rate for same currency as 1.0" in {
      val cache = mockCache(Some(mockRates))
      val service = new CachedRatesInterpreter[IO](cache)

      val result = service.get(Rate.Pair(Currency.USD, Currency.USD)).unsafeRunSync()
      result.isRight shouldBe true
      result.foreach { r => r.pair shouldBe Rate.Pair(Currency.USD, Currency.USD); r.price shouldBe Price(1.0) }
    }

    "should return direct USD rate" in {
      val cache = mockCache(Some(mockRates))
      val service = new CachedRatesInterpreter[IO](cache)

      val result = service.get(Rate.Pair(Currency.USD, Currency.EUR)).unsafeRunSync()
      result.map(_.price.value) shouldBe Right(0.85)
    }

    "should calculate cross rate" in {
      val cache = mockCache(Some(mockRates))
      val service = new CachedRatesInterpreter[IO](cache)

      val result = service.get(Rate.Pair(Currency.EUR, Currency.JPY)).unsafeRunSync()
      result.isRight shouldBe true
      val value: Double = result.fold(_ => 0.0, r => r.price.value.toDouble)
      assert(value > 129.0 && value < 131.0)
    }

    "should return ServiceUnavailable when cache empty" in {
      val cache = mockCache(None)
      val service = new CachedRatesInterpreter[IO](cache)

      val result = service.get(Rate.Pair(Currency.USD, Currency.EUR)).unsafeRunSync()
      result.isLeft shouldBe true
    }

    "should return PairNotFound for missing pair" in {
      val cache = mockCache(Some(mockRates))
      val service = new CachedRatesInterpreter[IO](cache)

      val result = service.get(Rate.Pair(Currency.AUD, Currency.CAD)).unsafeRunSync()
      result.isLeft shouldBe true
    }
  }
}
