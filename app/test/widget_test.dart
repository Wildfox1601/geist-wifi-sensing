import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geist_app/screens/login_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('Login restores the saved backend address', (tester) async {
    SharedPreferences.setMockInitialValues({'backend_ip': '192.0.2.10'});

    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));
    await tester.pumpAndSettle();

    expect(find.text('192.0.2.10'), findsOneWidget);
    expect(find.text('LOG IN'), findsOneWidget);
  });
}
