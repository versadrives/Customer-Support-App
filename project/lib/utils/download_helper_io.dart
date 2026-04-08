import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

Future<void> downloadBytesImpl(Uint8List bytes, String filename) async {
  if (Platform.isAndroid) {
    final storage = await Permission.storage.request();
    if (!storage.isGranted) {
      final manage = await Permission.manageExternalStorage.request();
      if (!manage.isGranted) {
        throw Exception('Storage permission denied.');
      }
    }
  }

  Directory? targetDir;
  if (Platform.isAndroid) {
    final dirs = await getExternalStorageDirectories(type: StorageDirectory.downloads);
    if (dirs != null && dirs.isNotEmpty) {
      targetDir = dirs.first;
    }
    targetDir ??= Directory('/storage/emulated/0/Download');
  }
  targetDir ??= await getApplicationDocumentsDirectory();
  await targetDir.create(recursive: true);

  final file = File('${targetDir.path}/$filename');
  await file.writeAsBytes(bytes, flush: true);
}
