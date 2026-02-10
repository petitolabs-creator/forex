package forex.services.valkey

import cats.effect.{ ConcurrentEffect, ContextShift, Resource }
import cats.syntax.functor._
import dev.profunktor.redis4cats.Redis
import dev.profunktor.redis4cats.connection.RedisClient
import dev.profunktor.redis4cats.data.RedisCodec
import dev.profunktor.redis4cats.effect.Log.Stdout._
import dev.profunktor.redis4cats.pubsub.PubSub
import forex.domain.{ Currency, Price, Rate, Timestamp }
import fs2.Stream
import io.circe._
import io.circe.syntax._
import io.circe.parser.decode
import io.circe.generic.extras.Configuration
import io.circe.generic.extras.semiauto.{ deriveConfiguredDecoder, deriveConfiguredEncoder }

/**
 * Valkey (Redis-compatible) client for centralized rate storage.
 *
 * Purpose:
 * - CronJob writes: Refresher fetches from One-Frame → writes to Valkey, then PUBLISHes to rates_updated
 * - API pods read: SUBSCRIBE to rates_updated; on message, GET rates and update in-memory cache
 *
 * Data structure:
 * - Key: "rates"
 * - Value: JSON array of all rates
 * - No TTL (overwritten by CronJob every 4 min)
 * - Channel: rates_updated (Refresher publishes after setRates so API pods sync event-driven)
 */
trait ValkeyClient[F[_]] {
  /**
   * Get all rates from Valkey.
   * Returns None if key doesn't exist (cold start).
   */
  def getRates(): F[Option[List[Rate]]]

  /**
   * Set all rates in Valkey.
   * Overwrites previous data atomically.
   */
  def setRates(rates: List[Rate]): F[Unit]

  /**
   * Publish to channel rates_updated so API pods (subscribers) sync from Valkey.
   * Refresher should call this after setRates for event-driven cache sync.
   */
  def publishRatesUpdated(): F[Unit]
}

object ValkeyClient {

  /** Channel name for notifying API pods that rates were updated in Valkey. */
  val RatesUpdatedChannel = "rates_updated"

  /**
   * Circe encoders/decoders for simple JSON format (not ADT-wrapped).
   * 
   * Format: {"from":"USD","to":"JPY","price":0.71,"timestamp":"2026-02-10T..."}
   */
  private implicit val configuration: Configuration = Configuration.default

  private implicit val currencyEncoder: Encoder[Currency] =
    Encoder.instance[Currency](c => Json.fromString(Currency.show.show(c)))

  private implicit val currencyDecoder: Decoder[Currency] =
    Decoder.instance[Currency] { cursor =>
      cursor.as[String].flatMap { str =>
        Currency.fromString(str) match {
          case Some(c) => Right(c)
          case None => Left(DecodingFailure(s"Invalid currency: $str", cursor.history))
        }
      }
    }

  private implicit val priceEncoder: Encoder[Price] =
    Encoder[BigDecimal].contramap(_.value)

  private implicit val priceDecoder: Decoder[Price] =
    Decoder[BigDecimal].map(Price.apply)

  private implicit val timestampEncoder: Encoder[Timestamp] =
    Encoder[String].contramap(_.value.toString)

  private implicit val timestampDecoder: Decoder[Timestamp] =
    Decoder[String].map(s => Timestamp(java.time.OffsetDateTime.parse(s)))

  private implicit val pairEncoder: Encoder[Rate.Pair] =
    deriveConfiguredEncoder[Rate.Pair]

  private implicit val pairDecoder: Decoder[Rate.Pair] =
    deriveConfiguredDecoder[Rate.Pair]

  private implicit val rateEncoder: Encoder[Rate] =
    deriveConfiguredEncoder[Rate]

  private implicit val rateDecoder: Decoder[Rate] =
    deriveConfiguredDecoder[Rate]

  private val stringCodec = RedisCodec.Utf8

  /**
   * Create Valkey client (GET/SET rates + publish to rates_updated).
   */
  def make[F[_]: ConcurrentEffect: ContextShift](
    uri: String
  ): Resource[F, ValkeyClient[F]] = {
    RedisClient[F].from(uri).flatMap { client =>
      Redis[F].fromClient(client, stringCodec).flatMap { redis =>
        makePublisherConnection[F](client).map { publishOne =>
          new ValkeyClient[F] {
            private val ratesKey = "rates"

            override def getRates(): F[Option[List[Rate]]] =
              redis.get(ratesKey).map {
                case Some(json) =>
                  decode[List[Rate]](json).toOption
                case None =>
                  None
              }

            override def setRates(rates: List[Rate]): F[Unit] = {
              val json = rates.asJson.noSpaces
              redis.set(ratesKey, json)
            }

            override def publishRatesUpdated(): F[Unit] =
              publishOne()
          }
        }
      }
    }
  }

  /** Create a dedicated publisher connection and return a thunk that publishes one message to rates_updated. */
  private def makePublisherConnection[F[_]: ConcurrentEffect: ContextShift](
    client: RedisClient
  ): Resource[F, () => F[Unit]] = {
    PubSub.mkPublisherConnection[F, String, String](client, stringCodec).map { pubSub =>
      val channel = dev.profunktor.redis4cats.data.RedisChannel(ValkeyClient.RatesUpdatedChannel)
      val sink = pubSub.publish(channel)
      () => Stream.emit("1").covary[F].through(sink).compile.drain
    }
  }

  /**
   * Create a stream that emits Unit whenever the Refresher publishes to rates_updated.
   * API pods use this as the sync trigger (event-driven) instead of polling every 150s.
   */
  def subscribeRatesUpdated[F[_]: ConcurrentEffect: ContextShift](
    uri: String
  ): Resource[F, fs2.Stream[F, Unit]] = {
    RedisClient[F].from(uri).flatMap { client =>
      PubSub.mkSubscriberConnection[F, String, String](client, stringCodec).map { sub =>
        val channel = dev.profunktor.redis4cats.data.RedisChannel(ValkeyClient.RatesUpdatedChannel)
        sub.subscribe(channel).as(())
      }
    }
  }
}
