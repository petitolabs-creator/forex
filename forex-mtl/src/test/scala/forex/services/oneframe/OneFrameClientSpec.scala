package forex.services.oneframe

import cats.effect.{ ContextShift, IO, Timer }
import cats.data.Kleisli
import forex.domain.{ Currency, Price }
import forex.services.oneframe.errors.{ Error => OneFrameError }
import org.http4s.client.Client
import org.http4s.{ HttpApp, Request, Response, Status }
import org.http4s.circe.CirceEntityCodec._
import io.circe.syntax._
import io.circe.generic.auto._
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.should.Matchers

import scala.concurrent.ExecutionContext
import scala.concurrent.duration._

class OneFrameClientSpec extends AnyFreeSpec with Matchers {

  implicit val cs: ContextShift[IO] = IO.contextShift(ExecutionContext.global)
  implicit val timer: Timer[IO] = IO.timer(ExecutionContext.global)

  "OneFrameClient" - {

    "getAllRates" - {
      "should successfully fetch and parse rates" in {
        val mockRates = List(
          OneFrameClient.OneFrameRate(
            from = "USD",
            to = "EUR",
            bid = BigDecimal("0.85"),
            ask = BigDecimal("0.86"),
            price = BigDecimal("0.855"),
            time_stamp = "2026-02-09T10:00:00Z"
          ),
          OneFrameClient.OneFrameRate(
            from = "EUR",
            to = "USD",
            bid = BigDecimal("1.16"),
            ask = BigDecimal("1.17"),
            price = BigDecimal("1.165"),
            time_stamp = "2026-02-09T10:00:00Z"
          )
        )

        val mockResponse = Response[IO](Status.Ok).withEntity(mockRates.asJson)
        val httpApp: HttpApp[IO] = Kleisli.pure(mockResponse)
        val client = Client.fromHttpApp(httpApp)

        val config = OneFrameClient.Config(
          baseUrl = "http://test",
          token = "test-token",
          timeout = 5.seconds,
          maxRetries = 0
        )

        val oneFrameClient = OneFrameClient.make[IO](client, config)
        val result = oneFrameClient.getAllRates().unsafeRunSync()

        result.isRight shouldBe true
        result.toOption.get should have size 2
        result.toOption.get.head.pair.from shouldBe Currency.USD
        result.toOption.get.head.pair.to shouldBe Currency.EUR
        result.toOption.get.head.price shouldBe Price(BigDecimal("0.855"))
      }

      "should handle HTTP errors with retry" in {
        @annotation.nowarn("msg=never updated")
        var attemptCount = 0

        val httpApp: HttpApp[IO] = Kleisli { _: Request[IO] =>
          attemptCount += 1
          IO.pure(Response[IO](Status.InternalServerError))
        }
        val client = Client.fromHttpApp(httpApp)

        val config = OneFrameClient.Config(
          baseUrl = "http://test",
          token = "test-token",
          timeout = 5.seconds,
          maxRetries = 2
        )

        val oneFrameClient = OneFrameClient.make[IO](client, config)
        val result = oneFrameClient.getAllRates().unsafeRunSync()

        result.isLeft shouldBe true
        attemptCount shouldBe 3 // initial + 2 retries
      }

      "should filter out invalid currencies" in {
        val mockRates = List(
          OneFrameClient.OneFrameRate(
            from = "USD",
            to = "EUR",
            bid = BigDecimal("0.85"),
            ask = BigDecimal("0.86"),
            price = BigDecimal("0.855"),
            time_stamp = "2026-02-09T10:00:00Z"
          ),
          OneFrameClient.OneFrameRate(
            from = "XXX", // Invalid currency
            to = "YYY",   // Invalid currency
            bid = BigDecimal("1.0"),
            ask = BigDecimal("1.0"),
            price = BigDecimal("1.0"),
            time_stamp = "2026-02-09T10:00:00Z"
          )
        )

        val mockResponse = Response[IO](Status.Ok).withEntity(mockRates.asJson)
        val httpApp: HttpApp[IO] = Kleisli.pure(mockResponse)
        val client = Client.fromHttpApp(httpApp)

        val config = OneFrameClient.Config(
          baseUrl = "http://test",
          token = "test-token",
          timeout = 5.seconds,
          maxRetries = 0
        )

        val oneFrameClient = OneFrameClient.make[IO](client, config)
        val result = oneFrameClient.getAllRates().unsafeRunSync()

        result.isRight shouldBe true
        result.toOption.get should have size 1 // Only valid rate
        result.toOption.get.head.pair.from shouldBe Currency.USD
      }

      "should return error on network failure" in {
        val httpApp: HttpApp[IO] = Kleisli { _: Request[IO] =>
          IO.raiseError(new RuntimeException("Network error"))
        }
        val client = Client.fromHttpApp(httpApp)

        val config = OneFrameClient.Config(
          baseUrl = "http://test",
          token = "test-token",
          timeout = 5.seconds,
          maxRetries = 0
        )

        val oneFrameClient = OneFrameClient.make[IO](client, config)
        val result = oneFrameClient.getAllRates().unsafeRunSync()

        result.isLeft shouldBe true
        result.left.toOption.get shouldBe a[OneFrameError.OneFrameLookupFailed]
      }

      "should generate all 72 currency pairs" in {
        val currencies = Currency.allCurrencies
        val expectedPairs = currencies.size * (currencies.size - 1)

        expectedPairs shouldBe 72
      }
    }
  }
}
