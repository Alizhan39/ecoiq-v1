/// Uniform error shape the rest of the app reacts to, regardless of
/// whether it came from Dio (real backend) or MockApiClient. Screens
/// switch on `type`, not on HTTP status codes, so swapping the client
/// implementation never touches UI code.
enum EcoIqApiErrorType {
  network,
  unauthorized,
  forbiddenSubscriptionRequired,
  notFound,
  server,
  unknown,
}

class EcoIqApiException implements Exception {
  const EcoIqApiException(this.type, this.message, {this.statusCode});

  final EcoIqApiErrorType type;
  final String message;
  final int? statusCode;

  @override
  String toString() => 'EcoIqApiException($type, $statusCode): $message';
}
