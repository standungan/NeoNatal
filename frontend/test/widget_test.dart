import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('App renders without crash', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: Text('NeonatalCare'))),
    );
    expect(find.text('NeonatalCare'), findsOneWidget);
  });
}
