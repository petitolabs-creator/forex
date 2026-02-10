package forex.services.valkey

import cats.effect.{ ContextShift, IO, Timer }
import forex.domain.{ Currency, Price, Rate, Timestamp }
import org.scalatest.Tag
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.should.Matchers

import java.time.OffsetDateTime
import scala.concurrent.ExecutionContext

/** Tag for tests that require a running Valkey. Excluded from default `sbt test`. */
object ValkeyRequired extends Tag("forex.ValkeyRequired")

/**
 * Integration tests for ValkeyClient. Require a running Valkey/Redis instance.
 * Run with: docker run -d -p 6379:6379 valkey/valkey:7
 * Run these tests: sbt "testOnly *ValkeyClientSpec"
 */
class ValkeyClientSpec extends AnyFreeSpec with Matchers {

  implicit val cs: ContextShift[IO] = IO.contextShift(ExecutionContext.global)
  implicit val timer: Timer[IO] = IO.timer(ExecutionContext.global)

  // Check if Valkey is running
  private lazy val isValkeyRunning: Boolean = {
    try {
      ValkeyClient.make[IO]("redis://localhost:6379").use { client =>
        client.getRates().map(_ => true)
      }.unsafeRunSync()
      true
    } catch {
      case _: Exception => false
    }
  }

  "ValkeyClient" - {

    "getRates" - {
      "should return None when key doesn't exist" taggedAs ValkeyRequired in {
        assume(isValkeyRunning, "Valkey not running on localhost:6379")
        val test = ValkeyClient.make[IO]("redis://localhost:6379").use { client =>
          for {
            // Clear any existing data
            _ <- client.setRates(List.empty)
            // Try to get rates from empty key
            result <- client.getRates()
          } yield result
        }

        val result = test.unsafeRunSync()
        // Empty list serialized to JSON will return Some(List.empty)
        result shouldBe Some(List.empty)
      }

      "should return rates after setting them" taggedAs ValkeyRequired in {
        assume(isValkeyRunning, "Valkey not running on localhost:6379")
        val rates = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.parse("2026-02-10T00:00:00Z"))
          ),
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.JPY),
            price = Price(BigDecimal("110.25")),
            timestamp = Timestamp(OffsetDateTime.parse("2026-02-10T00:00:00Z"))
          )
        )

        val test = ValkeyClient.make[IO]("redis://localhost:6379").use { client =>
          for {
            _      <- client.setRates(rates)
            result <- client.getRates()
          } yield result
        }

        val result = test.unsafeRunSync()
        result shouldBe Some(rates)
      }
    }

    "setRates" - {
      "should overwrite previous rates atomically" taggedAs ValkeyRequired in {
        assume(isValkeyRunning, "Valkey not running on localhost:6379")
        val rates1 = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal("0.85")),
            timestamp = Timestamp(OffsetDateTime.parse("2026-02-10T00:00:00Z"))
          )
        )

        val rates2 = List(
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.JPY),
            price = Price(BigDecimal("110.25")),
            timestamp = Timestamp(OffsetDateTime.parse("2026-02-10T00:00:00Z"))
          ),
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.GBP),
            price = Price(BigDecimal("0.75")),
            timestamp = Timestamp(OffsetDateTime.parse("2026-02-10T00:00:00Z"))
          )
        )

        val test = ValkeyClient.make[IO]("redis://localhost:6379").use { client =>
          for {
            _       <- client.setRates(rates1)
            after1  <- client.getRates()
            _       <- client.setRates(rates2)
            after2  <- client.getRates()
          } yield (after1, after2)
        }

        val (after1, after2) = test.unsafeRunSync()
        after1 shouldBe Some(rates1)
        after2 shouldBe Some(rates2)
      }

      "should handle empty rate list" taggedAs ValkeyRequired in {
        assume(isValkeyRunning, "Valkey not running on localhost:6379")
        val test = ValkeyClient.make[IO]("redis://localhost:6379").use { client =>
          for {
            _      <- client.setRates(List.empty)
            result <- client.getRates()
          } yield result
        }

        val result = test.unsafeRunSync()
        result shouldBe Some(List.empty)
      }

      "should handle large rate lists" taggedAs ValkeyRequired in {
        assume(isValkeyRunning, "Valkey not running on localhost:6379")
        val largeRateList = (1 to 100).map { i =>
          Rate(
            pair = Rate.Pair(Currency.USD, Currency.EUR),
            price = Price(BigDecimal(s"0.$i")),
            timestamp = Timestamp(OffsetDateTime.parse("2026-02-10T00:00:00Z"))
          )
        }.toList

        val test = ValkeyClient.make[IO]("redis://localhost:6379").use { client =>
          for {
            _      <- client.setRates(largeRateList)
            result <- client.getRates()
          } yield result
        }

        val result = test.unsafeRunSync()
        result.map(_.size) shouldBe Some(100)
      }
    }

    "error handling" - {
      "should fail gracefully with invalid Redis URI" in {
        val test = ValkeyClient.make[IO]("redis://invalid-host:9999").use { client =>
          client.getRates()
        }

        assertThrows[Exception] {
          test.unsafeRunSync()
        }
      }
    }
  }
}
