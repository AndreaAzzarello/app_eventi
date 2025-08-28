import 'package:flutter/material.dart';
import 'pages/map_page.dart'; // se usi la sola mappa

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const EventiApp());
}

class EventiApp extends StatelessWidget {
  const EventiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Eventi Vicini',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple)),
      home: const MapPage(), // oppure EventsListMapPage() se hai già quella
    );
  }
}
