package forex

import cats.effect.{ ConcurrentEffect, ContextShift, Resource, Timer }
import forex.config.ApplicationConfig
import forex.http.rates.RatesHttpRoutes
import forex.services._
import forex.services.cache.RatesCache
import forex.services.valkey.ValkeyClient
import forex.programs._
import org.http4s._
import org.http4s.implicits._
import org.http4s.server.middleware.{ AutoSlash, Timeout }

import scala.concurrent.ExecutionContext

class Module[F[_]: ConcurrentEffect: ContextShift: Timer](config: ApplicationConfig) {

  def createApp(implicit ec: ExecutionContext): Resource[F, HttpApp[F]] = {
    val _ = ec // kept for API compatibility
    for {
      valkeyClient <- ValkeyClient.make[F](config.valkey.uri)
      syncStream   <- ValkeyClient.subscribeRatesUpdated[F](config.valkey.uri)
      cacheAndJob  <- Resource.eval(RatesCache.make[F](valkeyClient, syncStream))
      (cache, syncJob) = cacheAndJob
      _ <- Resource.make(ConcurrentEffect[F].start(syncJob))(_.cancel)
    } yield httpApp(cache)
  }

  private def httpApp(cache: RatesCache[F]): HttpApp[F] = {
    val ratesService = RatesServices.cached[F](cache)
    val ratesProgram = RatesProgram[F](ratesService)
    val routes = new RatesHttpRoutes[F](ratesProgram).routes
    Timeout(config.http.timeout)(AutoSlash(routes).orNotFound)
  }

}
