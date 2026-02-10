package forex.services.rates.interpreters

import cats.effect.Sync
import cats.syntax.functor._
import forex.domain.Rate
import forex.services.oneframe.OneFrameClient
import forex.services.rates.Algebra
import forex.services.rates.errors._

class OneFrameLive[F[_]: Sync](oneFrameClient: OneFrameClient[F]) extends Algebra[F] {

  override def get(pair: Rate.Pair): F[Error Either Rate] = {
    oneFrameClient.getAllRates().map {
      case Right(rates) =>
        rates
          .find(rate => rate.pair == pair)
          .toRight(Error.RateLookupFailed(s"Rate not found for pair: $pair"))

      case Left(_) =>
        Left(Error.RateLookupFailed(s"One-Frame API error"))
    }
  }
}
