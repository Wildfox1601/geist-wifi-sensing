import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../utils/colors.dart';

enum LearningState { setup, recording, review, training, done }

class LearningScreen extends StatefulWidget {
  const LearningScreen({super.key});

  @override
  State<LearningScreen> createState() => _LearningScreenState();
}

class _LearningScreenState extends State<LearningScreen> {
  LearningState _currentState = LearningState.setup;
  final TextEditingController _nameController = TextEditingController();
  double _duration = 10.0;
  int _progress = 0;
  String _statusMessage = "Ready to record.";
  
  late IO.Socket _socket;

  @override
  void initState() {
    super.initState();
    _initSocket();
  }

  Future<void> _initSocket() async {
    final prefs = await SharedPreferences.getInstance();
    String savedIp = prefs.getString('backend_ip') ?? '127.0.0.1';
    String serverUrl = 'http://$savedIp:5000';

    _socket = IO.io(serverUrl, <String, dynamic>{
      'transports': ['websocket'],
      'autoConnect': true,
    });

    _socket.on('learning_update', (data) {
      if (!mounted) return;
      setState(() {
        String state = data['state'];
        if (data['message'] != null) {
          _statusMessage = data['message'];
        }

        if (state == 'learning') {
          _currentState = LearningState.recording;
          _progress = data['progress'] ?? 0;
        } else if (state == 'learning_done') {
          _currentState = LearningState.review;
          _progress = 100;
        } else if (state == 'training') {
          _currentState = LearningState.training;
        } else if (state == 'training_done') {
          _currentState = LearningState.done;
        } else if (state == 'restore_done') {
          _currentState = LearningState.setup;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(_statusMessage), backgroundColor: Colors.green),
          );
        }
      });
    });

    _socket.connect();
  }

  @override
  void dispose() {
    _socket.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _startRecording() {
    if (_nameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter an activity name."), backgroundColor: Colors.red),
      );
      return;
    }
    setState(() {
      _currentState = LearningState.recording;
      _progress = 0;
      _statusMessage = "Starting recording...";
    });
    _socket.emit('start_learning', {
      'activity_name': _nameController.text.trim(),
      'duration': _duration.toInt(),
    });
  }

  void _trainModel() {
    setState(() {
      _currentState = LearningState.training;
      _statusMessage = "Preparing to train...";
    });
    _socket.emit('train_model', {});
  }

  void _restoreOriginalModel() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Restore Original Model?"),
        content: const Text("This will overwrite your currently trained custom model with the factory default model. Proceed?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.alertRed),
            onPressed: () {
              Navigator.pop(context);
              _socket.emit('restore_model', {});
              setState(() {
                _statusMessage = "Restoring model...";
              });
            },
            child: const Text("Restore", style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text("Teach Geist"),
        backgroundColor: Colors.white,
        elevation: 0,
        titleTextStyle: const TextStyle(
          color: AppColors.darkText,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
        iconTheme: const IconThemeData(color: AppColors.darkText),
        actions: [
          IconButton(
            icon: const Icon(Icons.restore),
            tooltip: 'Restore Original Model',
            onPressed: _restoreOriginalModel,
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildStepper(),
              const SizedBox(height: 30),
              _buildContentCard(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStepper() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _buildStepIcon(1, "Setup", _currentState == LearningState.setup),
        _buildStepLine(),
        _buildStepIcon(2, "Record", _currentState == LearningState.recording || _currentState == LearningState.review),
        _buildStepLine(),
        _buildStepIcon(3, "Train", _currentState == LearningState.training),
        _buildStepLine(),
        _buildStepIcon(4, "Done", _currentState == LearningState.done),
      ],
    );
  }

  Widget _buildStepLine() {
    return Expanded(
      child: Container(height: 2, color: Colors.grey.shade300),
    );
  }

  Widget _buildStepIcon(int step, String label, bool isActive) {
    return Column(
      children: [
        CircleAvatar(
          radius: 16,
          backgroundColor: isActive ? AppColors.primary : Colors.grey.shade300,
          child: Text(
            step.toString(),
            style: TextStyle(
              color: isActive ? Colors.white : Colors.grey.shade600,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
            color: isActive ? AppColors.primary : Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  Widget _buildContentCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: _buildCurrentStateContent(),
    );
  }

  Widget _buildCurrentStateContent() {
    switch (_currentState) {
      case LearningState.setup:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Define New Activity",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            const Text(
              "Enter a name for the specific motion you want Geist to learn.",
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _nameController,
              decoration: InputDecoration(
                labelText: "Activity Name (e.g., Jumping)",
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                prefixIcon: const Icon(Icons.directions_run),
              ),
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("Recording Duration:", style: TextStyle(fontWeight: FontWeight.bold)),
                Text("${_duration.toInt()} sec", style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold)),
              ],
            ),
            Slider(
              value: _duration,
              min: 5,
              max: 30,
              divisions: 5,
              activeColor: AppColors.primary,
              onChanged: (val) => setState(() => _duration = val),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.fiber_manual_record, color: Colors.white),
                label: const Text("Start Recording", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.alertRed,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: _startRecording,
              ),
            ),
          ],
        );
      case LearningState.recording:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const SizedBox(height: 20),
            Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 120,
                  height: 120,
                  child: CircularProgressIndicator(
                    value: _progress / 100,
                    strokeWidth: 8,
                    backgroundColor: Colors.grey.shade200,
                    valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
                  ),
                ),
                Text(
                  "$_progress%",
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppColors.primary),
                ),
              ],
            ),
            const SizedBox(height: 30),
            Text(
              "Perform '${_nameController.text}' in front of the sensor now!",
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(_statusMessage, style: const TextStyle(color: Colors.grey)),
          ],
        );
      case LearningState.review:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 60),
            const SizedBox(height: 20),
            const Text(
              "Recording Complete",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              _statusMessage,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 30),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => setState(() => _currentState = LearningState.setup),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 15),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: const Text("Retake"),
                  ),
                ),
                const SizedBox(width: 15),
                Expanded(
                  child: ElevatedButton(
                    onPressed: _trainModel,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(vertical: 15),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: const Text("Train Model", style: TextStyle(color: Colors.white)),
                  ),
                ),
              ],
            ),
          ],
        );
      case LearningState.training:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const SizedBox(height: 20),
            const CircularProgressIndicator(),
            const SizedBox(height: 30),
            const Text(
              "Training AI Model...",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              _statusMessage,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 10),
            const Text(
              "This usually takes 30-60 seconds. Please wait.",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.orange, fontSize: 12),
            ),
          ],
        );
      case LearningState.done:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Icon(Icons.celebration, color: AppColors.primary, size: 60),
            const SizedBox(height: 20),
            const Text(
              "Success!",
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              "Geist has successfully learned to recognize '${_nameController.text}'.",
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey, fontSize: 16),
            ),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                child: const Text("Return to Dashboard", style: TextStyle(color: Colors.white)),
              ),
            ),
          ],
        );
    }
  }
}
