# ui_scaffold1.py
# ---------------------------------------------------------
# Flutter UI Scaffold (Part 1/2) for BenefiSocial
# - Supabase OAuth (GitHub/Google)
# - GoRouter auth guard
# - API client hitting FastAPI with Supabase JWT
# - Screens: SignIn, Home (Help + Profile tabs),
#            RFH list/create/detail(+match), Profile view/update
# Part 2 will add Content/QA/Projects/Events/Notifications.
# ---------------------------------------------------------
import os, stat
from pathlib import Path
from textwrap import dedent as D

ROOT = Path.cwd() / "frontend"

def w(path: Path, content: str, exe=False, skip=False):
    if skip and path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(D(content).strip() + "\n", encoding="utf-8")
    if exe:
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)

def main():
    # ---------------- Top-level ----------------
    w(ROOT / ".gitignore", """
        .dart_tool/
        .idea/
        .vscode/
        build/
        .flutter-plugins
        .flutter-plugins-dependencies
        .packages
        pubspec.lock
        .DS_Store
    """)
    w(ROOT / "README.md", """
        # BenefiSocial — Flutter UI (Part 1)

        This is a runnable MVP shell:
        - Supabase OAuth (GitHub/Google)
        - RFH list/create/detail (+match)
        - Profile view/update
        - GoRouter auth guard
        - API client calls your FastAPI backend

        ## First run
        ```bash
        bash create_flutter_app.sh   # runs `flutter create .` if needed
        flutter pub get
        # Edit lib/config.dart (SUPABASE + BACKEND_BASE_URL)
        flutter run -d chrome
        ```
        Login with GitHub/Google, then try creating an RFH and viewing matches.
    """)
    w(ROOT / "create_flutter_app.sh", """
        #!/usr/bin/env bash
        set -e
        if ! command -v flutter >/dev/null 2>&1; then
          echo "Flutter not found in PATH. Please install Flutter SDK."; exit 1
        fi
        if [ ! -f "pubspec.yaml" ] || [ ! -d "android" ] || [ ! -d "web" ]; then
          echo "Running: flutter create ."
          flutter create .
        else
          echo "Flutter skeleton exists. Skipping flutter create."
        fi
        echo "Done. Next: flutter pub get"
    """, exe=True)

    # ---------------- Pubspec & lint ----------------
    w(ROOT / "pubspec.yaml", """
        name: benefisocial
        description: BenefiSocial MVP UI (Part 1)
        publish_to: "none"
        version: 0.1.0+1

        environment:
          sdk: ">=3.3.0 <4.0.0"

        dependencies:
          flutter:
            sdk: flutter
          cupertino_icons: ^1.0.6
          supabase_flutter: ^2.5.6
          go_router: ^14.2.3
          http: ^1.2.2
          intl: ^0.19.0

        dev_dependencies:
          flutter_test:
            sdk: flutter
          flutter_lints: ^4.0.0

        flutter:
          uses-material-design: true
          assets:
            - assets/
    """)
    w(ROOT / "analysis_options.yaml", """
        include: package:flutter_lints/flutter.yaml
        linter:
          rules:
            prefer_const_constructors: true
            avoid_print: true
    """)

    # ---------------- Config & Bootstrap ----------------
    w(ROOT / "lib/config.dart", """
        // Fill these with your real values (required)
        const SUPABASE_URL = "https://YOUR_PROJECT.supabase.co";
        const SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY";
        // Backend (FastAPI) base URL, e.g., http://127.0.0.1:8000
        const BACKEND_BASE_URL = "http://127.0.0.1:8000";
        const API_PREFIX = "/api";
    """)
    w(ROOT / "lib/main.dart", """
        import 'package:flutter/material.dart';
        import 'package:supabase_flutter/supabase_flutter.dart';
        import 'config.dart';
        import 'routes.dart';

        Future<void> main() async {
          WidgetsFlutterBinding.ensureInitialized();
          await Supabase.initialize(url: SUPABASE_URL, anonKey: SUPABASE_ANON_KEY);
          runApp(const BenefiApp());
        }

        class BenefiApp extends StatelessWidget {
          const BenefiApp({super.key});
          @override
          Widget build(BuildContext context) {
            return MaterialApp.router(
              title: 'BenefiSocial',
              theme: ThemeData(
                colorSchemeSeed: Colors.teal,
                useMaterial3: true,
              ),
              routerConfig: appRouter,
            );
          }
        }
    """)

    # ---------------- Router ----------------
    w(ROOT / "lib/routes.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import 'package:supabase_flutter/supabase_flutter.dart';
        import 'screens/auth/sign_in_screen.dart';
        import 'screens/home/home_shell.dart';
        import 'screens/rfh/rfh_create_screen.dart';
        import 'screens/rfh/rfh_detail_screen.dart';

        final _supabase = Supabase.instance.client;

        final appRouter = GoRouter(
          initialLocation: '/',
          redirect: (ctx, state) {
            final sess = _supabase.auth.currentSession;
            final loggingIn = state.fullPath == '/signin';
            if (sess == null && !loggingIn) return '/signin';
            if (sess != null && loggingIn) return '/';
            return null;
          },
          routes: [
            GoRoute(
              path: '/signin',
              name: 'signin',
              builder: (ctx, st) => const SignInScreen(),
            ),
            ShellRoute(
              builder: (ctx, st, child) => HomeShell(child: child),
              routes: [
                GoRoute(path: '/', name: 'home', builder: (c, s) => const SizedBox()),
                GoRoute(path: '/rfh/new', name: 'rfh_new', builder: (c, s) => const RFHCreateScreen()),
                GoRoute(path: '/rfh/:id', name: 'rfh_detail', builder: (c, s) => RFHDetailScreen(id: s.pathParameters['id']!)),
              ],
            ),
          ],
        );
    """)

    # ---------------- Services ----------------
    w(ROOT / "lib/services/api_client.dart", """
        import 'dart:convert';
        import 'package:http/http.dart' as http;
        import 'package:supabase_flutter/supabase_flutter.dart';
        import '../config.dart';

        class ApiClient {
          final _client = http.Client();

          Uri _u(String path, [Map<String, dynamic>? q]) =>
              Uri.parse(BACKEND_BASE_URL + API_PREFIX + path).replace(queryParameters: q);

          Map<String, String> _headers({bool jsonBody = false}) {
            final token = Supabase.instance.client.auth.currentSession?.accessToken;
            final h = <String, String>{
              'Accept': 'application/json',
              if (jsonBody) 'Content-Type': 'application/json',
              if (token != null) 'Authorization': 'Bearer $token',
            };
            return h;
          }

          // Health (useful while wiring)
          Future<bool> health() async {
            final r = await _client.get(_u("/healthz"), headers: _headers());
            return r.statusCode == 200 && jsonDecode(r.body)['status'] == 'ok';
          }

          // ------- Profile -------
          Future<Map<String, dynamic>?> me() async {
            final r = await _client.get(_u("/profiles/me"), headers: _headers());
            if (r.statusCode == 200) return jsonDecode(r.body);
            return null;
          }

          Future<bool> updateProfile(Map body) async {
            final r = await _client.put(_u("/profiles/me"),
                headers: _headers(jsonBody: True), body: jsonEncode(body));
            return r.statusCode == 200;
          }

          // ------- RFH -------
          Future<List<dynamic>> listRFH({String? q, String? tag}) async {
            final r = await _client.get(_u("/rfh", {
              if (q != null) "q": q,
              if (tag != null) "tag": tag,
            }), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          Future<Map<String, dynamic>?> getRFH(String id) async {
            final r = await _client.get(_u("/rfh/$id"), headers: _headers());
            return r.statusCode == 200 ? jsonDecode(r.body) : null;
          }

          Future<String?> createRFH(Map body) async {
            final r = await _client.post(_u("/rfh"),
                headers: _headers(jsonBody: True), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          Future<List<dynamic>> matchRFH(String id) async {
            final r = await _client.get(_u("/match/$id"), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }
        }

        final api = ApiClient();

        // Tiny fix because Dart is capital-T True in string 🤓
        const True = true;
    """)

    # ---------------- Widgets ----------------
    w(ROOT / "lib/widgets/common.dart", """
        import 'package:flutter/material.dart';

        class AppScaffold extends StatelessWidget {
          final String title;
          final Widget body;
          final List<Widget>? actions;
          final Widget? floating;
          const AppScaffold({super.key, required this.title, required this.body, this.actions, this.floating});
          @override
          Widget build(BuildContext context) {
            return Scaffold(
              appBar: AppBar(title: Text(title), actions: actions),
              body: SafeArea(child: body),
              floatingActionButton: floating,
            );
          }
        }

        class Loading extends StatelessWidget {
          const Loading({super.key});
          @override
          Widget build(BuildContext context) => const Center(child: CircularProgressIndicator());
        }

        class Empty extends StatelessWidget {
          final String text;
          const Empty(this.text, {super.key});
          @override
          Widget build(BuildContext context) => Center(child: Text(text));
        }
    """)

    # ---------------- Auth ----------------
    w(ROOT / "lib/screens/auth/sign_in_screen.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import 'package:supabase_flutter/supabase_flutter.dart';

        class SignInScreen extends StatefulWidget {
          const SignInScreen({super.key});
          @override
          State<SignInScreen> createState() => _SignInScreenState();
        }

        class _SignInScreenState extends State<SignInScreen> {
          bool _loading = false;

          Future<void> _login(Provider provider) async {
            setState(() => _loading = true);
            try {
              await Supabase.instance.client.auth.signInWithOAuth(provider);
              if (mounted) context.go('/');
            } catch (e) {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Login error: $e')));
            } finally {
              if (mounted) setState(() => _loading = false);
            }
          }

          @override
          Widget build(BuildContext context) {
            return Scaffold(
              body: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text('BenefiSocial', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          const Text('Sign in to continue'),
                          const SizedBox(height: 18),
                          ElevatedButton.icon(
                            onPressed: _loading ? null : () => _login(Provider.github),
                            icon: const Icon(Icons.code),
                            label: const Text('Continue with GitHub'),
                          ),
                          const SizedBox(height: 8),
                          ElevatedButton.icon(
                            onPressed: _loading ? null : () => _login(Provider.google),
                            icon: const Icon(Icons.g_mobiledata),
                            label: const Text('Continue with Google'),
                          ),
                          const SizedBox(height: 12),
                          if (_loading) const CircularProgressIndicator(),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            );
          }
        }
    """)

    # ---------------- Home shell (2 tabs only in Part 1) ----------------
    w(ROOT / "lib/screens/home/home_shell.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import '../rfh/rfh_list_screen.dart';
        import '../profile/profile_screen.dart';

        class HomeShell extends StatefulWidget {
          final Widget child;
          const HomeShell({super.key, required this.child});
          @override
          State<HomeShell> createState() => _HomeShellState();
        }

        class _HomeShellState extends State<HomeShell> {
          int _idx = 0;
          final _pages = const [
            RFHListScreen(),
            ProfileScreen(),
          ];
          @override
          Widget build(BuildContext context) {
            return Scaffold(
              body: SafeArea(child: _pages[_idx]),
              bottomNavigationBar: NavigationBar(
                selectedIndex: _idx,
                onDestinationSelected: (i)=> setState(()=>_idx=i),
                destinations: const [
                  NavigationDestination(icon: Icon(Icons.help_outline), label: "Help"),
                  NavigationDestination(icon: Icon(Icons.person_outline), label: "Profile"),
                ],
              ),
              floatingActionButton: _idx == 0
                ? FloatingActionButton(
                    onPressed: ()=>context.push('/rfh/new'),
                    child: const Icon(Icons.add),
                  )
                : null,
            );
          }
        }
    """)

    # ---------------- RFH screens ----------------
    w(ROOT / "lib/screens/rfh/rfh_list_screen.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class RFHListScreen extends StatefulWidget {
          const RFHListScreen({super.key});
          @override
          State<RFHListScreen> createState() => _RFHListScreenState();
        }

        class _RFHListScreenState extends State<RFHListScreen> {
          late Future<List<dynamic>> _f;
          @override
          void initState() {
            super.initState();
            _f = api.listRFH();
          }
          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Help Requests",
              body: FutureBuilder(
                future: _f,
                builder: (c, s) {
                  if (!s.hasData) return const Loading();
                  final items = s.data as List<dynamic>;
                  if (items.isEmpty) return const Empty("No requests yet.");
                  return ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, __)=> const Divider(height: 1),
                    itemBuilder: (ctx, i) {
                      final r = items[i] as Map<String, dynamic>;
                      return ListTile(
                        title: Text(r['title'] ?? ''),
                        subtitle: Text((r['body'] ?? '').toString()),
                        onTap: ()=> context.push('/rfh/${r['id']}'),
                      );
                    },
                  );
                },
              ),
            );
          }
        }
    """)
    w(ROOT / "lib/screens/rfh/rfh_create_screen.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class RFHCreateScreen extends StatefulWidget {
          const RFHCreateScreen({super.key});
          @override
          State<RFHCreateScreen> createState() => _RFHCreateScreenState();
        }

        class _RFHCreateScreenState extends State<RFHCreateScreen> {
          final _form = GlobalKey<FormState>();
          final _title = TextEditingController();
          final _body = TextEditingController();
          final _tags = TextEditingController(text: "addiction, mentoring");

          bool _anon = false;
          bool _saving = false;

          Future<void> _submit() async {
            if (!_form.currentState!.validate()) return;
            setState(()=>_saving=true);
            final id = await api.createRFH({
              "title": _title.text,
              "body": _body.text,
              "tags": _tags.text.split(",").map((e)=>e.trim().replaceAll(" ", "-")).where((e)=>e.isNotEmpty).toList(),
              "anonymous": _anon,
              "sensitivity": "normal",
              "language": "tr",
            });
            setState(()=>_saving=false);
            if (id != null && mounted) {
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Request created")));
              context.go('/rfh/$id');
            }
          }

          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "New Help Request",
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _form,
                  child: ListView(
                    children: [
                      TextFormField(controller: _title, decoration: const InputDecoration(labelText: "Title"), validator: (v)=> v==null||v.isEmpty? "Required": null),
                      TextFormField(controller: _body, decoration: const InputDecoration(labelText: "Details"), maxLines: 5),
                      TextFormField(controller: _tags, decoration: const InputDecoration(labelText: "Tags (comma-separated)")),
                      SwitchListTile(value: _anon, onChanged: (v)=>setState(()=>_anon=v), title: const Text("Anonymous")),
                      const SizedBox(height: 12),
                      ElevatedButton(onPressed: _saving? null : _submit, child: Text(_saving? "Saving..." : "Create")),
                    ],
                  ),
                ),
              ),
            );
          }
        }
    """)
    w(ROOT / "lib/screens/rfh/rfh_detail_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class RFHDetailScreen extends StatefulWidget {
          final String id;
          const RFHDetailScreen({super.key, required this.id});
          @override
          State<RFHDetailScreen> createState() => _RFHDetailScreenState();
        }

        class _RFHDetailScreenState extends State<RFHDetailScreen> {
          Map<String, dynamic>? rfh;
          List<dynamic> matches = [];
          bool loading = true;

          Future<void> _load() async {
            final rr = await api.getRFH(widget.id);
            final mm = await api.matchRFH(widget.id);
            setState(() { rfh = rr; matches = mm; loading = false; });
          }

          @override
          void initState() { super.initState(); _load(); }

          @override
          Widget build(BuildContext context) {
            if (loading) return const AppScaffold(title: "Loading", body: Loading());
            if (rfh == null) return const AppScaffold(title: "Not found", body: Empty("RFH not found"));
            return AppScaffold(
              title: rfh!['title'] ?? 'Help Request',
              body: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Text(rfh!['body'] ?? '', style: const TextStyle(fontSize: 16)),
                  const SizedBox(height: 12),
                  Text("Tags: ${(rfh!['tags'] as List?)?.join(', ') ?? '-'}"),
                  const Divider(),
                  const Text("Suggested Helpers", style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  if (matches.isEmpty) const Text("No matches yet."),
                  for (final m in matches)
                    ListTile(
                      leading: const CircleAvatar(child: Icon(Icons.person)),
                      title: Text(m['helper_id'] ?? ''),
                      subtitle: Text("Score: ${m['score']}"),
                      trailing: ElevatedButton(onPressed: (){}, child: const Text("Contact (TODO)")),
                    ),
                ],
              ),
            );
          }
        }
    """)

    # ---------------- Profile ----------------
    w(ROOT / "lib/screens/profile/profile_screen.dart", """
        import 'package:flutter/material.dart';
        import 'package:supabase_flutter/supabase_flutter.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class ProfileScreen extends StatefulWidget {
          const ProfileScreen({super.key});
          @override
          State<ProfileScreen> createState() => _ProfileScreenState();
        }

        class _ProfileScreenState extends State<ProfileScreen> {
          Map<String, dynamic>? profile;
          bool loading = true;

          final _name = TextEditingController();
          final _bio = TextEditingController();
          final _offers = TextEditingController();
          final _needs = TextEditingController();

          Future<void> _load() async {
            profile = await api.me();
            if (profile != null) {
              _name.text = (profile!['full_name'] ?? '') as String;
              _bio.text = (profile!['bio'] ?? '') as String;
              _offers.text = ((profile!['offers'] ?? []) as List).join(", ");
              _needs.text = ((profile!['needs'] ?? []) as List).join(", ");
            }
            setState(()=>loading=false);
          }

          @override
          void initState(){ super.initState(); _load(); }

          @override
          Widget build(BuildContext context) {
            if (loading) return const AppScaffold(title: "Profile", body: Loading());
            final user = Supabase.instance.client.auth.currentUser;
            return AppScaffold(
              title: "Profile",
              actions: [
                IconButton(
                  onPressed: () async {
                    await Supabase.instance.client.auth.signOut();
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Signed out")));
                    }
                  },
                  icon: const Icon(Icons.logout),
                )
              ],
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: ListView(
                  children: [
                    ListTile(
                      leading: const CircleAvatar(child: Icon(Icons.person)),
                      title: Text(user?.email ?? '(unknown)'),
                      subtitle: Text("id: ${user?.id}"),
                    ),
                    const Divider(),
                    TextField(controller: _name, decoration: const InputDecoration(labelText: "Full name")),
                    TextField(controller: _bio, decoration: const InputDecoration(labelText: "Bio"), maxLines: 3),
                    TextField(controller: _offers, decoration: const InputDecoration(labelText: "Offers (comma)")),
                    TextField(controller: _needs, decoration: const InputDecoration(labelText: "Needs (comma)")),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: () async {
                        final ok = await api.updateProfile({
                          "full_name": _name.text,
                          "bio": _bio.text,
                          "offers": _offers.text.split(",").map((e)=>e.trim()).where((e)=>e.isNotEmpty).toList(),
                          "needs": _needs.text.split(",").map((e)=>e.trim()).where((e)=>e.isNotEmpty).toList(),
                        });
                        if (ok && mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Updated")));
                        }
                      },
                      child: const Text("Save"),
                    )
                  ],
                ),
              ),
            );
          }
        }
    """)

    # ---------------- Assets dir ----------------
    (ROOT / "assets").mkdir(parents=True, exist_ok=True)

    print("✅ Flutter UI Part 1 scaffold created at:", ROOT)
    print("Next:")
    print("  cd frontend && bash create_flutter_app.sh && flutter pub get")
    print("  edit lib/config.dart and then: flutter run -d chrome")

if __name__ == "__main__":
    main()
