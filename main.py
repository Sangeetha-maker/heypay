import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:speech_to_text/speech_to_text.dart' as stt;


const String apiBase = "https://heypay.onrender.com";

void main() {
  runApp(const HeyPayApp());
}

class HeyPayApp extends StatelessWidget {
  const HeyPayApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HeyPay',
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF38BDF8),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const HeyPayHome(),
    );
  }
}

class HeyPayHome extends StatefulWidget {
  const HeyPayHome({super.key});

  @override
  State<HeyPayHome> createState() => _HeyPayHomeState();
}

class _HeyPayHomeState extends State<HeyPayHome> {
  final TextEditingController _cmdController = TextEditingController();
  Map<String, dynamic>? _parsed;
  Map<String, dynamic>? _result;
  bool _loading = false;

  late stt.SpeechToText _speech;
  bool _isListening = false;

  List<dynamic> _history = [];
  double _balance = 0;

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    try {
      final res = await http.get(Uri.parse("$apiBase/api/transactions"));
      final data = jsonDecode(res.body);
      setState(() {
        _balance = (data["balance"] as num).toDouble();
        _history = data["transactions"] as List<dynamic>;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("History error: $e")),
      );
    }
  }

  Future<void> _toggleListening() async {
    if (!_isListening) {
      bool available = await _speech.initialize(
        onStatus: (status) => print('Speech status: $status'),
        onError: (error) => print('Speech error: $error'),
      );
      if (available) {
        setState(() => _isListening = true);
        _speech.listen(
          onResult: (result) {
            setState(() {
              _cmdController.text = result.recognizedWords;
            });
          },
          listenFor: const Duration(seconds: 5),
          pauseFor: const Duration(seconds: 2),
          localeId: 'en_US',
        );
      }
    } else {
      setState(() => _isListening = false);
      _speech.stop();
    }
  }

  Future<void> _parseCommand() async {
    final text = _cmdController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _loading = true;
      _parsed = null;
      _result = null;
    });

    try {
      final res = await http.post(
        Uri.parse("$apiBase/api/parse-command"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"text": text, "language": "en"}),
      );
      final data = jsonDecode(res.body);
      setState(() {
        _parsed = data;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error: $e")),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _confirmPay() async {
    if (_parsed == null) return;
    final amount = _parsed!["amount"];
    final payee = _parsed!["payee"];
    if (amount == null || payee == null || amount == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Need valid amount and payee.")),
      );
      return;
    }

    setState(() {
      _loading = true;
      _result = null;
    });

    try {
      final res = await http.post(
        Uri.parse("$apiBase/api/confirm-transaction"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "action": "pay",
          "amount": amount,
          "payee": payee,
          "user_id": "demo-user",
        }),
      );
      final data = jsonDecode(res.body);
      setState(() {
        _result = data;
      });
      await _loadHistory();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error: $e")),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final parsed = _parsed;
    final result = _result;

    return Scaffold(
      appBar: AppBar(
        title: const Text("HeyPay – Voice UPI (Prototype)"),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              const SizedBox(height: 8),
              Text(
                "Speak or type your command:",
                style: Theme.of(context).textTheme.titleMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                "Balance: ₹${_balance.toStringAsFixed(2)}",
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _cmdController,
                style: const TextStyle(fontSize: 18),
                decoration: InputDecoration(
                  hintText: 'e.g. "Send 100 rupees to Ramesh"',
                  filled: true,
                  fillColor: Colors.black.withOpacity(0.2),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size.fromHeight(56),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(28),
                    ),
                    backgroundColor: _isListening
                        ? Colors.redAccent
                        : const Color(0xFF38BDF8),
                  ),
                  onPressed: _loading ? null : _toggleListening,
                  icon: Icon(_isListening ? Icons.mic : Icons.mic_none),
                  label: Text(
                    _isListening ? "Listening... Tap to stop" : "Tap to Speak",
                    style: const TextStyle(fontSize: 18),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    minimumSize: const Size.fromHeight(56),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(28),
                    ),
                  ),
                  onPressed: _loading ? null : _parseCommand,
                  child: _loading
                      ? const CircularProgressIndicator()
                      : const Text(
                          "Parse Command",
                          style: TextStyle(fontSize: 18),
                        ),
                ),
              ),
              const SizedBox(height: 16),
              if (parsed != null)
                Flexible(
                  child: Card(
                    color: Colors.blueGrey.shade900,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: SingleChildScrollView(
                        child: Column(
                          children: [
                            Text(
                              "Confirmation",
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(color: const Color(0xFF38BDF8)),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              "Action: ${parsed["action"]}\n"
                              "Amount: ${parsed["amount"] ?? "N/A"}\n"
                              "Payee: ${parsed["payee"] ?? "N/A"}",
                              style: const TextStyle(fontSize: 18),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 12),
                            if (parsed["action"] == "pay" &&
                                parsed["amount"] != null &&
                                parsed["payee"] != null)
                              Row(
                                children: [
                                  Expanded(
                                    child: ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: Colors.green,
                                        minimumSize:
                                            const Size.fromHeight(56),
                                      ),
                                      onPressed:
                                          _loading ? null : _confirmPay,
                                      child: const Text(
                                        "Confirm Pay",
                                        style: TextStyle(
                                            fontSize: 18,
                                            color: Colors.white),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: Colors.red,
                                        minimumSize:
                                            const Size.fromHeight(56),
                                      ),
                                      onPressed: _loading
                                          ? null
                                          : () {
                                              setState(() {
                                                _parsed = null;
                                                _result = null;
                                              });
                                            },
                                      child: const Text(
                                        "Cancel",
                                        style: TextStyle(
                                            fontSize: 18,
                                            color: Colors.white),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              if (result != null)
                Flexible(
                  child: Card(
                    color: Colors.blueGrey.shade900,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: SingleChildScrollView(
                        child: Column(
                          children: [
                            Text(
                              "Transaction Result",
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(color: const Color(0xFF38BDF8)),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              "Status: ${result["status"]}\n"
                              "Balance: ${result["balance"]}\n"
                              "${result["status"] == "success" ? "Paid ${result["amount"]} to ${result["payee"]}" : "Reason: ${result["reason"]}"}",
                              style: const TextStyle(fontSize: 18),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              Expanded(
                child: Card(
                  color: Colors.blueGrey.shade900,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Transaction History",
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(color: const Color(0xFF38BDF8)),
                        ),
                        const SizedBox(height: 8),
                        Expanded(
                          child: _history.isEmpty
                              ? const Center(
                                  child: Text(
                                    "No transactions yet.",
                                    style: TextStyle(fontSize: 16),
                                  ),
                                )
                              : ListView.builder(
                                  itemCount: _history.length,
                                  itemBuilder: (context, index) {
                                    final tx = _history[index];
                                    return ListTile(
                                      title: Text(
                                        "Paid ₹${tx["amount"]} to ${tx["payee"]}",
                                        style:
                                            const TextStyle(fontSize: 16),
                                      ),
                                    );
                                  },
                                ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
