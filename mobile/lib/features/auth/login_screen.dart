import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../design/tokens.dart';
import '../../state/providers.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _isSubmitting = false;
  String? _errorText;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _isSubmitting = true;
      _errorText = null;
    });

    try {
      final deviceInfo = ref.read(deviceInfoServiceProvider);
      final deviceId = await deviceInfo.getOrCreateDeviceId();
      final appVersion = await deviceInfo.getAppVersion();
      await ref.read(authServiceProvider.notifier).login(
            username: _usernameController.text.trim(),
            password: _passwordController.text,
            deviceId: deviceId,
            deviceName: deviceInfo.deviceName,
            platform: deviceInfo.platform,
            appVersion: appVersion,
          );
      // Navigation to /home happens automatically via the router's
      // redirect guard reacting to the auth-status change (router.dart).
    } on EcoIqApiException catch (e) {
      setState(() => _errorText = e.message);
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(EcoIqSpace.xl),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'EcoIQ',
                      style: Theme.of(context)
                          .textTheme
                          .headlineMedium
                          ?.copyWith(
                              fontWeight: FontWeight.w800,
                              color: EcoIqColors.accent),
                    ),
                    const SizedBox(height: 4),
                    Text('Know what your investment supports',
                        style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: EcoIqSpace.xl),
                    TextFormField(
                      controller: _usernameController,
                      autofillHints: const [AutofillHints.username],
                      textInputAction: TextInputAction.next,
                      decoration:
                          const InputDecoration(labelText: 'Username or email'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: EcoIqSpace.md),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      autofillHints: const [AutofillHints.password],
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: 'Password',
                        suffixIcon: IconButton(
                          tooltip: _obscurePassword
                              ? 'Show password'
                              : 'Hide password',
                          icon: Icon(_obscurePassword
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined),
                          onPressed: () => setState(
                              () => _obscurePassword = !_obscurePassword),
                        ),
                      ),
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Required' : null,
                    ),
                    if (_errorText != null) ...[
                      const SizedBox(height: EcoIqSpace.sm),
                      Text(_errorText!,
                          style: TextStyle(color: EcoIqColors.danger)),
                    ],
                    const SizedBox(height: EcoIqSpace.lg),
                    ElevatedButton(
                      onPressed: _isSubmitting ? null : _submit,
                      child: _isSubmitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Sign in'),
                    ),
                    const SizedBox(height: EcoIqSpace.md),
                    // PART 12: optional Apple / Google / Microsoft sign-in.
                    // No social-auth provider is wired to the Django backend
                    // yet (django-allauth / equivalent isn't installed --
                    // see the final report's "prepared, not operational").
                    // Buttons are intentionally omitted rather than shown
                    // disabled/fake.
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
