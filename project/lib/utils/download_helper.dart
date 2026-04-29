import 'dart:typed_data';

import 'download_helper_stub.dart'
    if (dart.library.html) 'download_helper_web.dart'
    if (dart.library.io) 'download_helper_io.dart';

Future<String> downloadBytes(Uint8List bytes, String filename) async {
  return await downloadBytesImpl(bytes, filename);
}

