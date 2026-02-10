package forex.services.oneframe

import cats.effect.{ Sync, Timer }
import cats.syntax.all._
import forex.domain.{ Currency, Price, Rate, Timestamp }
import forex.services.oneframe.errors.Error
import io.circe.Decoder
import io.circe.generic.semiauto._
import org.http4s.Method.GET
import org.http4s.circe.CirceEntityDecoder._
import org.http4s.client.Client
import org.http4s.{ Header, Headers, Request, Uri }
import org.typelevel.ci.CIString

import java.time.OffsetDateTime
import scala.concurrent.duration._

trait OneFrameClient[F[_]] {
  def getAllRates(): F[Error Either List[Rate]]
}

object OneFrameClient {

  // JSON response from One-Frame API
  case class OneFrameRate(
      from: String,
      to: String,
      bid: BigDecimal,
      ask: BigDecimal,
      price: BigDecimal,
      time_stamp: String
  )

  implicit val oneFrameRateDecoder: Decoder[OneFrameRate] = deriveDecoder[OneFrameRate]

  case class Config(
      baseUrl: String,
      token: String,
      timeout: FiniteDuration,
      maxRetries: Int
  )

  def make[F[_]: Sync: Timer](
      client: Client[F],
      config: Config
  ): OneFrameClient[F] = new OneFrameClient[F] {

    override def getAllRates(): F[Error Either List[Rate]] = {
      retryWithBackoff(fetchRatesOnce(), config.maxRetries, 100.millis)
        .map(rates => Right(rates): Error Either List[Rate])
        .handleErrorWith { error =>
          Sync[F].pure(Left(Error.OneFrameLookupFailed(error.getMessage)): Error Either List[Rate])
        }
    }

    private def fetchRatesOnce(): F[List[Rate]] = {
      val allPairs = buildAllPairs()
      val uri      = buildUri(config.baseUrl, allPairs)

      val request = Request[F](
        method = GET,
        uri = uri,
        headers = Headers(Header.Raw(CIString("token"), config.token))
      )

      client
        .expect[List[OneFrameRate]](request)
        .map(_.flatMap(toRate))
    }

    private def buildAllPairs(): List[String] = {
      for {
        from <- Currency.oneFrameCurrencies
        to   <- Currency.oneFrameCurrencies
        if from != to
      } yield s"${from.code}${to.code}"
    }

    private def buildUri(base: String, pairs: List[String]): Uri = {
      val baseUri = Uri.unsafeFromString(base)
      val pairParams = pairs.map(p => ("pair", Some(p)))
      baseUri.copy(query = org.http4s.Query.fromVector(pairParams.toVector))
    }

    private def toRate(oneFrameRate: OneFrameRate): Option[Rate] = {
      for {
        from <- Currency.fromString(oneFrameRate.from)
        to   <- Currency.fromString(oneFrameRate.to)
        timestamp = parseTimestamp(oneFrameRate.time_stamp)
      } yield Rate(
        pair = Rate.Pair(from, to),
        price = Price(oneFrameRate.price),
        timestamp = timestamp
      )
    }

    private def parseTimestamp(timestampStr: String): Timestamp = {
      try {
        Timestamp(OffsetDateTime.parse(timestampStr))
      } catch {
        case _: Exception => Timestamp.now
      }
    }

    // Exponential backoff retry
    private def retryWithBackoff[A](
        fa: F[A],
        retriesLeft: Int,
        delay: FiniteDuration
    ): F[A] = {
      fa.handleErrorWith { error =>
        if (retriesLeft > 0) {
          Timer[F].sleep(delay) *> retryWithBackoff(fa, retriesLeft - 1, delay * 2)
        } else {
          Sync[F].raiseError(error)
        }
      }
    }
  }
}
