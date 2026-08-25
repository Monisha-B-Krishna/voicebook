import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/app_data_provider.dart';
import 'providers/locale_provider.dart';
import 'services/api_service.dart';
import 'screens/home_shell.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const VoiceBookApp());
}

class VoiceBookApp extends StatelessWidget {
  const VoiceBookApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Set baseUrl to your deployed FastAPI backend when ready, e.g.:
        // ApiService(baseUrl: 'https://your-vps.com')
        Provider<ApiService>(create: (_) => ApiService()),
        ChangeNotifierProvider<AppDataProvider>(create: (_) => AppDataProvider()),
        ChangeNotifierProvider<LocaleProvider>(create: (_) => LocaleProvider()),
      ],
      child: MaterialApp(
        title: 'VoiceBook',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.theme,
        home: const HomeShell(),
      ),
    );
  }
}
