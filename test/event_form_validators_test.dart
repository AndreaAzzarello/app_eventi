import 'package:app_eventi/features/admin/event_form_validators.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('validateRequired', () {
    expect(validateRequired(null), 'Campo obbligatorio');
    expect(validateRequired('   '), 'Campo obbligatorio');
    expect(validateRequired('Concerto'), isNull);
    expect(validateRequired('x' * 121, max: 120), 'Massimo 120 caratteri');
  });

  test('validateOptionalUrl', () {
    expect(validateOptionalUrl(''), isNull);
    expect(validateOptionalUrl('https://example.com/a.jpg'), isNull);
    expect(validateOptionalUrl('http://example.com'), isNull);
    expect(validateOptionalUrl('example.com'), isNotNull);
    expect(validateOptionalUrl('javascript:alert(1)'), isNotNull);
    expect(validateOptionalUrl('https://'), isNotNull);
  });

  test('validateRange', () {
    final a = DateTime(2026, 11, 1, 21);
    expect(validateRange(a, a), isNull);
    expect(validateRange(a, a.add(const Duration(hours: 1))), isNull);
    expect(validateRange(a, a.subtract(const Duration(minutes: 1))), isNotNull);
  });

  test('validateCoords', () {
    expect(validateCoords(null, null), isNotNull);
    expect(validateCoords(0, 0), isNotNull);
    expect(validateCoords(44.64, 10.92), isNull);
  });

  test('parseTags pulisce, abbassa e toglie i doppioni', () {
    expect(parseTags(' Live, outdoor , ,live,KIDS'), ['live', 'outdoor', 'kids']);
    expect(parseTags(''), isEmpty);
  });
}
