using System;
using System.Diagnostics;
using System.IO;
using System.Windows;

namespace RedCord.Launcher;

public partial class MainWindow : Window
{
    private readonly string _logFile = Path.Combine("logs", "launcher.log");
    private Process? _runningProcess;

    public MainWindow()
    {
        InitializeComponent();
        Directory.CreateDirectory("logs");
        AppendLog("Launcher started.");
        RefreshStatus();
    }

    private void StartButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var exePath = Path.Combine("dist", "RedCord", "RedCord.exe");
            ProcessStartInfo psi;
            if (File.Exists(exePath))
            {
                psi = new ProcessStartInfo(exePath);
                AppendLog("Launching compiled RedCord.exe");
            }
            else
            {
                psi = new ProcessStartInfo("python", "-m redcord.main") { WorkingDirectory = ".." };
                AppendLog("Launching python -m redcord.main");
            }

            _runningProcess = Process.Start(psi);
            if (_runningProcess != null)
            {
                _runningProcess.EnableRaisingEvents = true;
                _runningProcess.Exited += (_, _) =>
                {
                    Dispatcher.Invoke(() =>
                    {
                        AppendLog("RedCord process exited. You can restart it.");
                        MessageBox.Show("RedCord завершился. Перезапустить вручную кнопкой Start RedCord.", "RedCord Launcher");
                    });
                };
            }
            StatusText.Text = "Status: RedCord running";
        }
        catch (Exception ex)
        {
            AppendLog($"Start failed: {ex.Message}");
            StatusText.Text = "Status: start failed";
        }
    }

    private void CheckDbButton_Click(object sender, RoutedEventArgs e)
    {
        // mock-safe check without touching PG internals
        var pgAvailable = Environment.GetEnvironmentVariable("DATABASE_URL") != null || File.Exists("..\\.env");
        StatusText.Text = $"Status: PostgreSQL {(pgAvailable ? "available" : "not configured")}";
        AppendLog(StatusText.Text);
    }

    private void RecoveryButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var p = Process.Start(new ProcessStartInfo("python", "-m redcord.main --recovery-check") { WorkingDirectory = ".." });
            AppendLog("Recovery check launched.");
            StatusText.Text = "Status: recovery check started";
        }
        catch (Exception ex)
        {
            AppendLog($"Recovery check failed: {ex.Message}");
        }
    }

    private void OpenLogsButton_Click(object sender, RoutedEventArgs e)
    {
        Process.Start(new ProcessStartInfo("explorer", "logs") { UseShellExecute = true });
    }

    private void RefreshStatus()
    {
        var exeFound = File.Exists(Path.Combine("dist", "RedCord", "RedCord.exe"));
        StatusText.Text = $"Status: executable {(exeFound ? "found" : "not found")}";
    }

    private void AppendLog(string message)
    {
        var line = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}{Environment.NewLine}";
        File.AppendAllText(_logFile, line);
        LogBox.AppendText(line);
        LogBox.ScrollToEnd();
    }
}
