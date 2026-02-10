package forex

import cats.effect.{ ExitCode, IO, IOApp }
import forex.config.ApplicationConfig
import forex.services.oneframe.OneFrameClient
import forex.services.refresher.RefresherService
import forex.services.valkey.ValkeyClient
import org.http4s.blaze.client.BlazeClientBuilder
import pureconfig.ConfigSource
import pureconfig.generic.auto._

import scala.concurrent.ExecutionContext

/**
 * Refresher executable for K8s CronJob.
 *
 * Usage:
 * - Runs as a K8s CronJob every 4 minutes
 * - Fetches all rates from One-Frame API
 * - Writes to Valkey for API pods to consume
 *
 * Configuration:
 * - Reads from application.conf
 * - Env vars: VALKEY_URL, ONEFRAME_URL, ONEFRAME_TOKEN
 *
 * Exit codes:
 * - 0: Success
 * - 1: Failure (will trigger K8s retry)
 */
object RefresherMain extends IOApp {

  override def run(args: List[String]): IO[ExitCode] = {
    // Load configuration from app namespace
    val configIO = IO {
      ConfigSource.default.at("app").loadOrThrow[ApplicationConfig]
    }

    configIO.flatMap { config =>
      // Get Valkey URL from config (supports env var override)
      val valkeyUrl = config.valkey.uri

      // Create HTTP client
      BlazeClientBuilder[IO](ExecutionContext.global)
        .withRequestTimeout(config.oneFrame.timeout)
        .resource
        .use { httpClient =>
          // Create Valkey client
          ValkeyClient.make[IO](valkeyUrl).use { valkeyClient =>
            // Create One-Frame client
            val oneFrameConfig = OneFrameClient.Config(
              baseUrl = config.oneFrame.baseUrl,
              token = config.oneFrame.token,
              timeout = config.oneFrame.timeout,
              maxRetries = config.oneFrame.maxRetries
            )
            val oneFrameClient = OneFrameClient.make[IO](httpClient, oneFrameConfig)

            // Create refresher service
            val refresher = RefresherService.make[IO](oneFrameClient, valkeyClient)

            // Run refresh
            refresher.refresh().flatMap {
              case Right(count) =>
                IO.delay(println(s"✅ Successfully refreshed $count rates")) *>
                  IO.pure(ExitCode.Success)

              case Left(error) =>
                IO.delay(System.err.println(s"❌ Refresh failed: $error")) *>
                  IO.pure(ExitCode.Error)
            }
          }
        }
    }.handleErrorWith { error =>
      IO.delay(System.err.println(s"❌ Fatal error: ${error.getMessage}")) *>
        IO.delay(error.printStackTrace()) *>
        IO.pure(ExitCode.Error)
    }
  }
}
