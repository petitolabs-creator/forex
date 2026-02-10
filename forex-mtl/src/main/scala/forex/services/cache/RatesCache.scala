package forex.services.cache

import cats.effect.{ Concurrent, Sync }
import cats.effect.concurrent.{ Deferred, Ref }
import cats.syntax.flatMap._
import cats.syntax.functor._
import cats.syntax.applicativeError._
import forex.domain.Rate
import forex.services.valkey.ValkeyClient
import fs2.Stream
import org.slf4j.LoggerFactory

/**
 * In-memory cache for rates.
 *
 * Event-driven sync: subscribes to Valkey channel rates_updated; on each message, fetches
 * rates from Valkey and updates cache. Initial sync on startup, then sync only when Refresher publishes.
 * Serves all API requests from memory (< 1ms latency).
 */
trait RatesCache[F[_]] {
  /**
   * Get all rates from cache.
   * Returns None if cache not initialized (cold start).
   */
  def getRates(): F[Option[List[Rate]]]

  /**
   * Update cache with new rates.
   */
  def updateRates(rates: List[Rate]): F[Unit]
}

object RatesCache {

  private val logger = LoggerFactory.getLogger(getClass)

  /**
   * Create in-memory cache with event-driven sync from Valkey.
   *
   * @param valkeyClient Valkey client for fetching rates (GET only; no pub/sub on this client)
   * @param syncTrigger   Stream that emits Unit whenever the Refresher publishes (e.g. SUBSCRIBE rates_updated).
   *                      On each emission we run one sync from Valkey.
   */
  def make[F[_]: Concurrent](
    valkeyClient: ValkeyClient[F],
    syncTrigger: Stream[F, Unit]
  ): F[(RatesCache[F], F[Unit])] = {

    for {
      cacheRef   <- Ref.of[F, Option[List[Rate]]](None)
      initialized <- Deferred[F, Unit]

      cache = new RatesCache[F] {
        override def getRates(): F[Option[List[Rate]]] =
          cacheRef.get
        override def updateRates(rates: List[Rate]): F[Unit] =
          cacheRef.set(Some(rates))
      }

      sync = syncOnce(cacheRef, initialized, valkeyClient)

      // Initial sync, then run sync on every syncTrigger emission (event-driven)
      syncJob = (Stream.eval(sync) ++ syncTrigger.evalMap(_ => sync)).compile.drain
    } yield (cache, syncJob)
  }

  private def syncOnce[F[_]: Concurrent](
    cacheRef: Ref[F, Option[List[Rate]]],
    initialized: Deferred[F, Unit],
    valkeyClient: ValkeyClient[F]
  ): F[Unit] = {
    (for {
      _ <- Sync[F].delay(logger.info("Syncing rates from Valkey..."))
      startTime = System.currentTimeMillis()
      ratesOpt <- valkeyClient.getRates()
      _ <- ratesOpt match {
        case Some(rates) =>
          for {
            _ <- cacheRef.set(Some(rates))
            duration = System.currentTimeMillis() - startTime
            _ <- Sync[F].delay(logger.info(s"✓ Synced ${rates.size} rates from Valkey in ${duration}ms"))
            _ <- initialized.complete(()).attempt
          } yield ()
        case None =>
          Sync[F].delay(logger.warn("⚠ No rates in Valkey, keeping current cache"))
      }
    } yield ()).handleErrorWith { error =>
      Sync[F].delay(logger.error(s"✗ Sync failed: ${error.getMessage}", error))
    }
  }
}
