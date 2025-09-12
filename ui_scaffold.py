# ui_scaffold2.py
# ---------------------------------------------------------
# Flutter UI Scaffold (Part 2/2) for BenefiSocial
# - Adds tabs & screens: Content, Q&A, Projects, Events, Notifications
# - Upgrades routes and HomeShell
# - Expands ApiClient with corresponding endpoints
# This script OVERWRITES some Part 1 files with superset versions.
# ---------------------------------------------------------
import os, sys
from pathlib import Path
from textwrap import dedent as D

ROOT = Path.cwd() / "frontend"

def w(path: Path, content: str, *, exist_ok=True):
    if not exist_ok and path.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(D(content).strip() + "\n", encoding="utf-8")

def require(p: Path, hint: str):
    if not p.exists():
        raise SystemExit(f"❌ {hint} not found at {p}. Please run Part 1 (ui_scaffold1.py) first.")

def main():
    # Sanity checks (from Part 1)
    require(ROOT / "pubspec.yaml", "frontend skeleton")
    require(ROOT / "lib" / "routes.dart", "routes.dart (Part 1)")
    require(ROOT / "lib" / "services" / "api_client.dart", "api_client.dart (Part 1)")
    require(ROOT / "lib" / "screens" / "home" / "home_shell.dart", "home_shell.dart (Part 1)")

    # -----------------------------------------------------
    # Overwrite routes.dart with extended routes
    # -----------------------------------------------------
    w(ROOT / "lib" / "routes.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import 'package:supabase_flutter/supabase_flutter.dart';
        import 'screens/auth/sign_in_screen.dart';
        import 'screens/home/home_shell.dart';
        import 'screens/rfh/rfh_create_screen.dart';
        import 'screens/rfh/rfh_detail_screen.dart';
        import 'screens/qa/qa_create_question_screen.dart';
        import 'screens/content/content_create_screen.dart';
        import 'screens/projects/projects_create_screen.dart';
        import 'screens/events/events_create_screen.dart';

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
                // Create/detail screens (opened from FABs / lists)
                GoRoute(path: '/rfh/new', name: 'rfh_new', builder: (c, s) => const RFHCreateScreen()),
                GoRoute(path: '/rfh/:id', name: 'rfh_detail', builder: (c, s) => RFHDetailScreen(id: s.pathParameters['id']!)),
                GoRoute(path: '/qa/new', name: 'qa_new', builder: (c, s) => const QACreateQuestionScreen()),
                GoRoute(path: '/content/new', name: 'content_new', builder: (c, s) => const ContentCreateScreen()),
                GoRoute(path: '/projects/new', name: 'project_new', builder: (c, s) => const ProjectsCreateScreen()),
                GoRoute(path: '/events/new', name: 'event_new', builder: (c, s) => const EventsCreateScreen()),
              ],
            ),
          ],
        );
    """)

    # -----------------------------------------------------
    # Overwrite HomeShell with 7 tabs (Help, Content, Q&A, Projects, Events, Profile, Alerts)
    # -----------------------------------------------------
    w(ROOT / "lib" / "screens" / "home" / "home_shell.dart", """
        import 'package:flutter/material.dart';
        import 'package:go_router/go_router.dart';
        import '../rfh/rfh_list_screen.dart';
        import '../content/content_list_screen.dart';
        import '../qa/qa_list_screen.dart';
        import '../projects/projects_list_screen.dart';
        import '../events/events_list_screen.dart';
        import '../profile/profile_screen.dart';
        import '../notifications/notifications_screen.dart';

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
            ContentListScreen(),
            QAListScreen(),
            ProjectsListScreen(),
            EventsListScreen(),
            ProfileScreen(),
            NotificationsScreen(),
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
                  NavigationDestination(icon: Icon(Icons.menu_book_outlined), label: "Content"),
                  NavigationDestination(icon: Icon(Icons.question_answer_outlined), label: "Q&A"),
                  NavigationDestination(icon: Icon(Icons.group_work_outlined), label: "Projects"),
                  NavigationDestination(icon: Icon(Icons.event), label: "Events"),
                  NavigationDestination(icon: Icon(Icons.person_outline), label: "Profile"),
                  NavigationDestination(icon: Icon(Icons.notifications_none), label: "Alerts"),
                ],
              ),
              floatingActionButton: switch(_idx) {
                0 => FloatingActionButton(
                      onPressed: ()=>context.push('/rfh/new'),
                      child: const Icon(Icons.add),
                    ),
                1 => FloatingActionButton(
                      onPressed: ()=>context.push('/content/new'),
                      child: const Icon(Icons.add),
                    ),
                2 => FloatingActionButton(
                      onPressed: ()=>context.push('/qa/new'),
                      child: const Icon(Icons.add),
                    ),
                3 => FloatingActionButton(
                      onPressed: ()=>context.push('/projects/new'),
                      child: const Icon(Icons.add),
                    ),
                4 => FloatingActionButton(
                      onPressed: ()=>context.push('/events/new'),
                      child: const Icon(Icons.add),
                    ),
                _ => null,
              },
            );
          }
        }
    """)

    # -----------------------------------------------------
    # Overwrite ApiClient with full set of endpoints
    # -----------------------------------------------------
    w(ROOT / "lib" / "services" / "api_client.dart", """
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

          // --------- Health/Auth/Profile ----------
          Future<bool> health() async {
            final r = await _client.get(_u("/healthz"), headers: _headers());
            return r.statusCode == 200 && jsonDecode(r.body)['status'] == 'ok';
          }

          Future<Map<String, dynamic>?> me() async {
            final r = await _client.get(_u("/profiles/me"), headers: _headers());
            if (r.statusCode == 200) return jsonDecode(r.body);
            return null;
          }

          Future<bool> updateProfile(Map body) async {
            final r = await _client.put(_u("/profiles/me"),
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            return r.statusCode == 200;
          }

          // --------- RFH ----------
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
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          Future<List<dynamic>> matchRFH(String id) async {
            final r = await _client.get(_u("/match/$id"), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          // --------- Content ----------
          Future<List<dynamic>> listContent({String? q, String? tag}) async {
            final r = await _client.get(_u("/content", {
              if (q != null) "q": q,
              if (tag != null) "tag": tag,
            }), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          Future<String?> createContent(Map body) async {
            final r = await _client.post(_u("/content"),
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          // --------- Q&A ----------
          Future<List<dynamic>> listQuestions({String? q, String? tag}) async {
            final r = await _client.get(_u("/qa/questions", {
              if (q != null) "q": q,
              if (tag != null) "tag": tag,
            }), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          Future<String?> createQuestion(Map body) async {
            final r = await _client.post(_u("/qa/questions"),
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          Future<List<dynamic>> listAnswers(String qid) async {
            final r = await _client.get(_u("/qa/questions/$qid/answers"), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          Future<String?> createAnswer(Map body) async {
            final r = await _client.post(_u("/qa/answers"),
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          // --------- Projects ----------
          Future<List<dynamic>> listProjects() async {
            final r = await _client.get(_u("/projects"), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          Future<String?> createProject(Map body) async {
            final r = await _client.post(_u("/projects"),
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          Future<bool> applyProject(String id, String? message) async {
            final r = await _client.post(_u("/projects/$id/apply"),
                headers: _headers(jsonBody: true), body: jsonEncode({"message": message}));
            return r.statusCode == 200;
          }

          // --------- Events ----------
          Future<List<dynamic>> listEvents() async {
            final r = await _client.get(_u("/events"), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }

          Future<String?> createEvent(Map body) async {
            final r = await _client.post(_u("/events"),
                headers: _headers(jsonBody: true), body: jsonEncode(body));
            if (r.statusCode == 200) return jsonDecode(r.body)['id'];
            return null;
          }

          Future<bool> enrollEvent(String id) async {
            final r = await _client.post(_u("/events/$id/enroll"),
                headers: _headers(jsonBody: true), body: jsonEncode({}));
            return r.statusCode == 200;
          }

          // --------- Notifications ----------
          Future<List<dynamic>> myNotifications() async {
            final r = await _client.get(_u("/notifications"), headers: _headers());
            return r.statusCode == 200 ? (jsonDecode(r.body) as List) : [];
          }
        }

        final api = ApiClient();
    """)

    # -----------------------------------------------------
    # New Screens (Content)
    # -----------------------------------------------------
    w(ROOT / "lib" / "screens" / "content" / "content_list_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class ContentListScreen extends StatefulWidget {
          const ContentListScreen({super.key});
          @override
          State<ContentListScreen> createState() => _ContentListScreenState();
        }

        class _ContentListScreenState extends State<ContentListScreen> {
          late Future<List<dynamic>> _f;
          @override
          void initState(){ super.initState(); _f = api.listContent(); }
          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Content",
              body: FutureBuilder(
                future: _f,
                builder: (c, s){
                  if (!s.hasData) return const Loading();
                  final items = s.data as List<dynamic>;
                  if (items.isEmpty) return const Empty("No content yet.");
                  return ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, __)=> const Divider(height: 1),
                    itemBuilder: (ctx, i){
                      final x = items[i] as Map<String, dynamic>;
                      return ListTile(
                        title: Text(x['title'] ?? ''),
                        subtitle: Text(x['summary'] ?? ''),
                      );
                    },
                  );
                },
              ),
            );
          }
        }
    """)
    w(ROOT / "lib" / "screens" / "content" / "content_create_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class ContentCreateScreen extends StatefulWidget {
          const ContentCreateScreen({super.key});
          @override
          State<ContentCreateScreen> createState() => _ContentCreateScreenState();
        }

        class _ContentCreateScreenState extends State<ContentCreateScreen> {
          final _form = GlobalKey<FormState>();
          final _title = TextEditingController();
          final _summary = TextEditingController();
          final _body = TextEditingController();
          final _tags = TextEditingController(text: "leadership");
          String _type = "guide";
          bool _saving = false;

          Future<void> _submit() async {
            if (!_form.currentState!.validate()) return;
            setState(()=>_saving=true);
            final id = await api.createContent({
              "type": _type,
              "title": _title.text,
              "summary": _summary.text,
              "body": _body.text,
              "evidence": "n_a",
              "visibility": "public",
              "language": "tr",
              "tags": _tags.text.split(",").map((e)=>e.trim().replaceAll(" ", "-")).where((e)=>e.isNotEmpty).toList(),
            });
            setState(()=>_saving=false);
            if (id!=null && mounted) {
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Content created")));
              Navigator.pop(context);
            }
          }

          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "New Content",
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _form,
                  child: ListView(
                    children: [
                      DropdownButtonFormField(
                        value: _type,
                        items: const [
                          DropdownMenuItem(value: "best_practice", child: Text("Best Practice")),
                          DropdownMenuItem(value: "guide", child: Text("Guide")),
                          DropdownMenuItem(value: "story", child: Text("Story")),
                          DropdownMenuItem(value: "case_study", child: Text("Case Study")),
                          DropdownMenuItem(value: "video", child: Text("Video (link in body)")),
                        ],
                        onChanged: (v)=> setState(()=> _type = v as String),
                        decoration: const InputDecoration(labelText: "Type"),
                      ),
                      TextFormField(controller: _title, decoration: const InputDecoration(labelText: "Title"), validator: (v)=> v==null||v.isEmpty? "Required": null),
                      TextFormField(controller: _summary, decoration: const InputDecoration(labelText: "Summary")),
                      TextFormField(controller: _body, decoration: const InputDecoration(labelText: "Body"), maxLines: 6),
                      TextFormField(controller: _tags, decoration: const InputDecoration(labelText: "Tags (comma)")),
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

    # -----------------------------------------------------
    # New Screens (Q&A)
    # -----------------------------------------------------
    w(ROOT / "lib" / "screens" / "qa" / "qa_list_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class QAListScreen extends StatefulWidget {
          const QAListScreen({super.key});
          @override
          State<QAListScreen> createState() => _QAListScreenState();
        }

        class _QAListScreenState extends State<QAListScreen> {
          late Future<List<dynamic>> _f;
          @override
          void initState(){ super.initState(); _f = api.listQuestions(); }
          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Q&A",
              body: FutureBuilder(
                future: _f,
                builder: (c, s){
                  if (!s.hasData) return const Loading();
                  final items = s.data as List<dynamic>;
                  if (items.isEmpty) return const Empty("No questions yet.");
                  return ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, __)=> const Divider(height: 1),
                    itemBuilder: (ctx,i){
                      final x = items[i] as Map<String, dynamic>;
                      return ListTile(
                        title: Text(x['title'] ?? ''),
                        subtitle: Text((x['body'] ?? '').toString()),
                      );
                    },
                  );
                },
              ),
            );
          }
        }
    """)
    w(ROOT / "lib" / "screens" / "qa" / "qa_create_question_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class QACreateQuestionScreen extends StatefulWidget {
          const QACreateQuestionScreen({super.key});
          @override
          State<QACreateQuestionScreen> createState() => _QACreateQuestionScreenState();
        }

        class _QACreateQuestionScreenState extends State<QACreateQuestionScreen> {
          final _form = GlobalKey<FormState>();
          final _title = TextEditingController();
          final _body = TextEditingController();
          final _tags = TextEditingController(text: "flutter, fastapi");

          bool _saving = false;

          Future<void> _submit() async {
            if (!_form.currentState!.validate()) return;
            setState(()=>_saving=true);
            final id = await api.createQuestion({
              "title": _title.text,
              "body": _body.text,
              "tags": _tags.text.split(",").map((e)=>e.trim()).where((e)=>e.isNotEmpty).toList(),
              "visibility": "public",
            });
            setState(()=>_saving=false);
            if (id!=null && mounted) {
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Question posted")));
              Navigator.pop(context);
            }
          }

          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Ask a Question",
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _form,
                  child: ListView(
                    children: [
                      TextFormField(controller: _title, decoration: const InputDecoration(labelText: "Title"), validator: (v)=> v==null||v.isEmpty? "Required": null),
                      TextFormField(controller: _body, decoration: const InputDecoration(labelText: "Body"), maxLines: 6),
                      TextFormField(controller: _tags, decoration: const InputDecoration(labelText: "Tags (comma)")),
                      const SizedBox(height: 12),
                      ElevatedButton(onPressed: _saving? null : _submit, child: Text(_saving? "Posting..." : "Post")),
                    ],
                  ),
                ),
              ),
            );
          }
        }
    """)

    # -----------------------------------------------------
    # New Screens (Projects)
    # -----------------------------------------------------
    w(ROOT / "lib" / "screens" / "projects" / "projects_list_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class ProjectsListScreen extends StatefulWidget {
          const ProjectsListScreen({super.key});
          @override
          State<ProjectsListScreen> createState() => _ProjectsListScreenState();
        }

        class _ProjectsListScreenState extends State<ProjectsListScreen> {
          late Future<List<dynamic>> _f;
          @override
          void initState(){ super.initState(); _f = api.listProjects(); }
          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Projects",
              body: FutureBuilder(
                future: _f,
                builder: (c, s){
                  if (!s.hasData) return const Loading();
                  final items = s.data as List<dynamic>;
                  if (items.isEmpty) return const Empty("No projects yet.");
                  return ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, __)=> const Divider(height: 1),
                    itemBuilder: (ctx, i){
                      final x = items[i] as Map<String, dynamic>;
                      return ListTile(
                        title: Text(x['title'] ?? ''),
                        subtitle: Text((x['description'] ?? '').toString()),
                        trailing: TextButton(
                          onPressed: () async {
                            final ok = await api.applyProject(x['id'], "Interested!");
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Applied (if open)")));
                            }
                          },
                          child: const Text("Apply"),
                        ),
                      );
                    },
                  );
                },
              ),
            );
          }
        }
    """)
    w(ROOT / "lib" / "screens" / "projects" / "projects_create_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class ProjectsCreateScreen extends StatefulWidget {
          const ProjectsCreateScreen({super.key});
          @override
          State<ProjectsCreateScreen> createState() => _ProjectsCreateScreenState();
        }

        class _ProjectsCreateScreenState extends State<ProjectsCreateScreen> {
          final _form = GlobalKey<FormState>();
          final _title = TextEditingController();
          final _desc = TextEditingController();
          final _roles = TextEditingController(text: "founder, flutter-dev");
          final _tags = TextEditingController(text: "ai-ml");

          bool _saving = false;

          Future<void> _submit() async {
            if (!_form.currentState!.validate()) return;
            setState(()=>_saving=true);
            final id = await api.createProject({
              "title": _title.text,
              "description": _desc.text,
              "needed_roles": _roles.text.split(",").map((e)=>e.trim()).where((e)=>e.isNotEmpty).toList(),
              "tags": _tags.text.split(",").map((e)=>e.trim()).where((e)=>e.isNotEmpty).toList(),
              "visibility": "public",
            });
            setState(()=>_saving=false);
            if (id!=null && mounted) {
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Project created")));
              Navigator.pop(context);
            }
          }

          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "New Project",
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _form,
                  child: ListView(
                    children: [
                      TextFormField(controller: _title, decoration: const InputDecoration(labelText: "Title"), validator: (v)=> v==null||v.isEmpty? "Required": null),
                      TextFormField(controller: _desc, decoration: const InputDecoration(labelText: "Description"), maxLines: 5),
                      TextFormField(controller: _roles, decoration: const InputDecoration(labelText: "Needed roles (comma)")),
                      TextFormField(controller: _tags, decoration: const InputDecoration(labelText: "Tags (comma)")),
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

    # -----------------------------------------------------
    # New Screens (Events)
    # -----------------------------------------------------
    w(ROOT / "lib" / "screens" / "events" / "events_list_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class EventsListScreen extends StatefulWidget {
          const EventsListScreen({super.key});
          @override
          State<EventsListScreen> createState() => _EventsListScreenState();
        }

        class _EventsListScreenState extends State<EventsListScreen> {
          late Future<List<dynamic>> _f;
          @override
          void initState(){ super.initState(); _f = api.listEvents(); }
          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Events",
              body: FutureBuilder(
                future: _f,
                builder: (c, s){
                  if (!s.hasData) return const Loading();
                  final items = s.data as List<dynamic>;
                  if (items.isEmpty) return const Empty("No events yet.");
                  return ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, __)=> const Divider(height: 1),
                    itemBuilder: (ctx, i){
                      final x = items[i] as Map<String, dynamic>;
                      return ListTile(
                        title: Text("${x['title']} • ${x['type']}"),
                        subtitle: Text((x['location'] ?? '').toString()),
                        trailing: ElevatedButton(
                          onPressed: () async {
                            await api.enrollEvent(x['id']);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Enrolled (if open)")));
                            }
                          },
                          child: const Text("Join"),
                        ),
                      );
                    },
                  );
                },
              ),
            );
          }
        }
    """)
    w(ROOT / "lib" / "screens" / "events" / "events_create_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class EventsCreateScreen extends StatefulWidget {
          const EventsCreateScreen({super.key});
          @override
          State<EventsCreateScreen> createState() => _EventsCreateScreenState();
        }

        class _EventsCreateScreenState extends State<EventsCreateScreen> {
          final _form = GlobalKey<FormState>();
          final _title = TextEditingController();
          final _desc = TextEditingController();
          final _location = TextEditingController(text: "https://meet.example.com/room");
          final _capacity = TextEditingController(text: "100");
          String _type = "webinar";
          DateTime _starts = DateTime.now().add(const Duration(days:1));

          bool _saving = false;

          Future<void> _submit() async {
            if (!_form.currentState!.validate()) return;
            setState(()=>_saving=true);
            final id = await api.createEvent({
              "title": _title.text,
              "description": _desc.text,
              "type": _type,
              "starts_at": _starts.toIso8601String(),
              "location": _location.text,
              "capacity": int.tryParse(_capacity.text),
              "tags": [],
              "visibility": "public",
            });
            setState(()=>_saving=false);
            if (id!=null && mounted) {
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Event created")));
              Navigator.pop(context);
            }
          }

          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "New Event",
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _form,
                  child: ListView(
                    children: [
                      TextFormField(controller: _title, decoration: const InputDecoration(labelText: "Title"), validator: (v)=> v==null||v.isEmpty? "Required": null),
                      TextFormField(controller: _desc, decoration: const InputDecoration(labelText: "Description"), maxLines: 4),
                      DropdownButtonFormField(
                        value: _type,
                        items: const [
                          DropdownMenuItem(value: "course", child: Text("Course")),
                          DropdownMenuItem(value: "webinar", child: Text("Webinar")),
                          DropdownMenuItem(value: "workshop", child: Text("Workshop")),
                        ],
                        onChanged: (v)=> setState(()=> _type = v as String),
                      ),
                      TextFormField(controller: _location, decoration: const InputDecoration(labelText: "Location (URL/venue)")),
                      TextFormField(controller: _capacity, decoration: const InputDecoration(labelText: "Capacity")),
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

    # -----------------------------------------------------
    # New Screen (Notifications)
    # -----------------------------------------------------
    w(ROOT / "lib" / "screens" / "notifications" / "notifications_screen.dart", """
        import 'package:flutter/material.dart';
        import '../../services/api_client.dart';
        import '../../widgets/common.dart';

        class NotificationsScreen extends StatefulWidget {
          const NotificationsScreen({super.key});
          @override
          State<NotificationsScreen> createState() => _NotificationsScreenState();
        }

        class _NotificationsScreenState extends State<NotificationsScreen> {
          late Future<List<dynamic>> _f;
          @override
          void initState(){ super.initState(); _f = api.myNotifications(); }
          @override
          Widget build(BuildContext context) {
            return AppScaffold(
              title: "Alerts",
              body: FutureBuilder(
                future: _f,
                builder: (c, s){
                  if (!s.hasData) return const Loading();
                  final items = s.data as List<dynamic>;
                  if (items.isEmpty) return const Empty("No notifications");
                  return ListView.separated(
                    itemCount: items.length,
                    separatorBuilder: (_, __)=> const Divider(height: 1),
                    itemBuilder: (ctx, i){
                      final x = items[i] as Map<String, dynamic>;
                      return ListTile(
                        title: Text(x['type'] ?? 'notification'),
                        subtitle: Text((x['payload'] ?? {}).toString()),
                      );
                    },
                  );
                },
              ),
            );
          }
        }
    """)

    print("✅ Flutter UI Part 2 applied to:", ROOT)
    print("Next:")
    print("  cd frontend && flutter pub get")
    print("  flutter run -d chrome")
    print("If you see CORS/auth issues, confirm lib/config.dart (backend URL) and Supabase OAuth redirect origins.")

if __name__ == "__main__":
    main()
