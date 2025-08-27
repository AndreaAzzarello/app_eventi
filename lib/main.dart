import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'features/map/map_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const EventiApp());
}

class EventiApp extends StatelessWidget {
  const EventiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Eventi Vicini',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const MapPage(),
    );
  }
}
