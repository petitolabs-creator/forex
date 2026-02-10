package forex.services.oneframe.errors

sealed trait Error extends Exception
object Error {
  final case class OneFrameLookupFailed(msg: String) extends Error
}
