package forex.services.rates

object errors {

  sealed trait Error
  object Error {
    final case class OneFrameLookupFailed(msg: String) extends Error
    final case class RateLookupFailed(msg: String) extends Error
    final case class ServiceUnavailable(msg: String) extends Error
    final case class PairNotFound(msg: String) extends Error
  }

}
