package forex.services.rates.interpreters

import cats.Applicative
import cats.syntax.functor._
import cats.syntax.either._
import cats.syntax.applicative._
import forex.services.rates.errors._
import forex.services.rates.Algebra
import forex.domain.{ Currency, Price, Rate }
import forex.services.cache.RatesCache

/**
 * RatesService that serves from in-memory cache.
 * 
 * Rate calculation:
 * - Same currency: 1.0
 * - From USD: direct lookup
 * - To USD: inverse (1 / rate)
 * - Cross-rates: divide USD rates (e.g., EUR/JPY = USD/JPY ÷ USD/EUR)
 */
class CachedRatesInterpreter[F[_]: Applicative](
  cache: RatesCache[F]
) extends Algebra[F] {

  override def get(pair: Rate.Pair): F[Error Either Rate] = {
    // Same currency
    if (pair.from == pair.to) {
      Rate(pair, Price(1.0), forex.domain.Timestamp.now).asRight[Error].pure[F]
    } else {
      cache.getRates().map {
        case Some(rates) =>
          calculateRate(rates, pair)
        
        case None =>
          Left(Error.ServiceUnavailable("Cache not initialized"))
      }
    }
  }
  
  private def calculateRate(rates: List[Rate], pair: Rate.Pair): Error Either Rate = {
    // Build lookup map: (from, to) -> rate
    val rateMap = rates.map(r => (r.pair.from, r.pair.to) -> r).toMap
    
    // Try direct lookup
    rateMap.get((pair.from, pair.to)) match {
      case Some(rate) =>
        Right(rate)
      
      case None =>
        // Try cross-rate calculation via USD
        val fromUsdOpt = rateMap.get((Currency.USD, pair.from))
        val toUsdOpt = rateMap.get((Currency.USD, pair.to))
        
        (fromUsdOpt, toUsdOpt) match {
          case (Some(fromUsd), Some(toUsd)) =>
            // Cross rate: to / from
            val crossPrice = toUsd.price.value / fromUsd.price.value
            val timestamp = if (fromUsd.timestamp.value.isAfter(toUsd.timestamp.value)) 
              fromUsd.timestamp 
            else 
              toUsd.timestamp
            
            Right(Rate(pair, Price(crossPrice), timestamp))
          
          case _ =>
            Left(Error.PairNotFound(s"${pair.from}/${pair.to}"))
        }
    }
  }
}
