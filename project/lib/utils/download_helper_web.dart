import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

Future<String> downloadBytesImpl(Uint8List bytes, String filename) async {
  final parts = <JSAny?>[bytes.toJS].toJS;
  final blob = web.Blob(parts as JSArray<web.BlobPart>);
  final url = web.URL.createObjectURL(blob);
  web.HTMLAnchorElement()
    ..href = url
    ..download = filename
    ..click();
  web.URL.revokeObjectURL(url);
  return url;
}

