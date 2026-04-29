import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

Future<String> downloadBytesImpl(Uint8List bytes, String filename) async {
  List<Directory> candidates = [];

  if (Platform.isAndroid) {
    candidates.add(Directory('/storage/emulated/0/Download'));
    final extDirs = await getExternalStorageDirectories(type: StorageDirectory.documents);
    if (extDirs != null && extDirs.isNotEmpty) {
      candidates.add(extDirs.first);
    }
  }

  candidates.add(await getApplicationDocumentsDirectory());

  for (final dir in candidates) {
    try {
      if (!await dir.exists()) await dir.create(recursive: true);
      final file = File('${dir.path}/$filename');
      await file.writeAsBytes(bytes, flush: true);
      return file.path;
    } catch (_) {
      continue;
    }
  }

  throw Exception('Could not save file to any location');
}
