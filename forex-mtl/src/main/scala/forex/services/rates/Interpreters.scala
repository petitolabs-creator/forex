package forex.services.rates

import cats.Applicative
import cats.effect.Sync
import forex.services.oneframe.OneFrameClient
import forex.services.cache.RatesCache
import interpreters._

object Interpreters {
  def dummy[F[_]: Applicative]: Algebra[F] = new OneFrameDummy[F]()

  def live[F[_]: Sync](oneFrameClient: OneFrameClient[F]): Algebra[F] =
    new OneFrameLive[F](oneFrameClient)
  
  def cached[F[_]: Applicative](cache: RatesCache[F]): Algebra[F] =
    new CachedRatesInterpreter[F](cache)
}
