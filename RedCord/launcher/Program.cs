using System;
using System.Windows;

namespace RedCord.Launcher;

public class Program
{
    [STAThread]
    public static void Main()
    {
        var app = new App();
        app.Run();
    }
}
