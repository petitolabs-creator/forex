package forex.config

import scala.concurrent.duration.FiniteDuration

case class ApplicationConfig(
    http: HttpConfig,
    oneFrame: OneFrameConfig,
    valkey: ValkeyConfig
)

case class HttpConfig(
    host: String,
    port: Int,
    timeout: FiniteDuration
)

case class OneFrameConfig(
    baseUrl: String,
    token: String,
    timeout: FiniteDuration,
    maxRetries: Int
)

case class ValkeyConfig(
    uri: String
)
