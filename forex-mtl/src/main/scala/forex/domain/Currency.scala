package forex.domain

import cats.Show

/** ISO 4217 currency code (3-letter). Supports all current ISO 4217 currencies. */
final case class Currency(code: String)

object Currency {

  // One-Frame API supports these 9; we request pairs only among them.
  val USD: Currency = Currency("USD")
  val EUR: Currency = Currency("EUR")
  val GBP: Currency = Currency("GBP")
  val JPY: Currency = Currency("JPY")
  val AUD: Currency = Currency("AUD")
  val CAD: Currency = Currency("CAD")
  val CHF: Currency = Currency("CHF")
  val NZD: Currency = Currency("NZD")
  val SGD: Currency = Currency("SGD")

  val oneFrameCurrencies: List[Currency] =
    List(USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD, SGD)

  /** All currencies we fetch from One-Frame (same as oneFrameCurrencies). */
  val allCurrencies: List[Currency] = oneFrameCurrencies

  /** All valid ISO 4217 alphabetic codes (current + common). API accepts any of these. */
  val AllCodes: Set[String] = Set(
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD",
    "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS",
    "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS", "KHR",
    "KMF", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL",
    "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR",
    "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR",
    "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG", "QAR",
    "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD",
    "SHP", "SLE", "SLL", "SOS", "SRD", "SSP", "STN", "SYP", "SZL", "THB",
    "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS", "UAH", "UGX",
    "USD", "UYU", "UZS", "VES", "VND", "VUV", "WST", "XAF", "XCD", "XOF",
    "XPF", "YER", "ZAR", "ZMW", "ZWL"
  )

  implicit val show: Show[Currency] = Show.show(_.code)

  def fromString(s: String): Option[Currency] = {
    val c = s.toUpperCase
    if (c.length == 3 && AllCodes.contains(c)) Some(Currency(c))
    else None
  }
}
