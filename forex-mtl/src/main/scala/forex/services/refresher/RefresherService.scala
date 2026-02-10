package forex.services.refresher

import cats.effect.Sync
import cats.syntax.applicativeError._
import cats.syntax.flatMap._
import cats.syntax.functor._
import forex.services.oneframe.OneFrameClient
import forex.services.valkey.ValkeyClient
import org.slf4j.LoggerFactory

/**
 * Refresher service for CronJob.
 *
 * Responsibility:
 * - Fetch all rates from One-Frame API
 * - Write to Valkey for API pods to consume
 * - Run every 4 minutes (360 calls/day)
 *
 * Error handling:
 * - Retries handled by OneFrameClient
 * - On failure: log error, don't overwrite Valkey (keep stale data)
 * - Alert on consecutive failures (handled by K8s monitoring)
 */
class RefresherService[F[_]: Sync](
  oneFrameClient: OneFrameClient[F],
  valkeyClient: ValkeyClient[F]
) {

  private val logger = LoggerFactory.getLogger(getClass)

  /**
   * Refresh rates from One-Frame API and update Valkey.
   *
   * Returns:
   * - Right(count) on success
   * - Left(error) on failure
   */
  def refresh(): F[Either[String, Int]] = {
    val startTime = System.currentTimeMillis()

    (for {
      _     <- Sync[F].delay(logger.info("Starting refresh from One-Frame API..."))

      // Fetch all rates from One-Frame
      result <- oneFrameClient.getAllRates()

      count <- result match {
        case Right(rates) =>
          for {
            // Write to Valkey
            _ <- valkeyClient.setRates(rates)
            // Notify API pods via pub/sub so they sync immediately (event-driven)
            _ <- valkeyClient.publishRatesUpdated()

            duration = System.currentTimeMillis() - startTime
            _ <- Sync[F].delay(logger.info(s"✅ Refreshed ${rates.size} rates in ${duration}ms"))
          } yield (Right(rates.size): Either[String, Int])

        case Left(error) =>
          val duration = System.currentTimeMillis() - startTime
          val errorMsg = s"One-Frame API error: $error"
          Sync[F].delay {
            logger.error(s"❌ Refresh failed after ${duration}ms: $errorMsg")
            (Left(errorMsg): Either[String, Int])
          }
      }
    } yield count).handleErrorWith { throwable =>
      val duration = System.currentTimeMillis() - startTime
      val errorMsg = s"Unexpected error: ${throwable.getMessage}"
      Sync[F].delay {
        logger.error(s"❌ Refresh failed after ${duration}ms: $errorMsg", throwable)
        Left(errorMsg)
      }
    }
  }
}

object RefresherService {
  def make[F[_]: Sync](
    oneFrameClient: OneFrameClient[F],
    valkeyClient: ValkeyClient[F]
  ): RefresherService[F] =
    new RefresherService[F](oneFrameClient, valkeyClient)
}
