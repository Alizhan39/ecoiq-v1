import 'package:ecoiq_app/shared/widgets/status_chip.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // PART 17 of the app spec: "Ethical-risk categories must never be
  // conveyed only by red, amber or green colours." Every tone must render
  // BOTH a distinct icon AND the text label -- never color alone.
  for (final tone in EcoIqStatusTone.values) {
    testWidgets('$tone status chip renders an icon and its text label',
        (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: EcoIqStatusChip(label: 'Test Status', tone: tone)),
      ));

      expect(find.text('Test Status'), findsOneWidget);
      expect(find.byType(Icon), findsOneWidget);
    });
  }

  testWidgets(
      'different tones render visually distinct icons, not just different colors',
      (tester) async {
    final icons = <IconData>{};
    for (final tone in EcoIqStatusTone.values) {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(body: EcoIqStatusChip(label: 'x', tone: tone)),
      ));
      final icon = tester.widget<Icon>(find.byType(Icon));
      icons.add(icon.icon!);
    }
    expect(icons.length, EcoIqStatusTone.values.length,
        reason: 'every tone must use a distinct icon shape');
  });
}
