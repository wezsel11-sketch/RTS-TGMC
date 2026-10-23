#region Copyright & License Information
// TGMC mod code. Licensed under the GNU General Public License, version 3 or later,
// the same licence as OpenRA, whose traits this file extends.
#endregion

using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

namespace OpenRA.Mods.TGMC.UtilityCommands
{
	// A TGMC sound can decode fine elsewhere and still hang OpenRA's own Ogg reader (mecha/overload_stop.ogg did, freezing any game that
	// played it). This decodes every file the way the game does, to the end, and names the ones that fail or hang.
	sealed class CheckSoundsCommand : IUtilityCommand
	{
		string IUtilityCommand.Name => "--check-sounds";

		bool IUtilityCommand.ValidateArguments(string[] args) { return args.Length >= 2; }

		[Desc("DIRECTORY", "Decode every .ogg in DIRECTORY with the game's sound loaders; list those that fail or take over 10 seconds.")]
		void IUtilityCommand.Run(Utility utility, string[] args)
		{
			var loaders = utility.ModData.SoundLoaders;
			var files = Directory.GetFiles(args[1], "*.ogg").OrderBy(f => f).ToList();
			var bad = 0;
			foreach (var file in files)
			{
				var work = Task.Run(() =>
				{
					using var stream = File.OpenRead(file);
					ISoundFormat sound = null;
					if (!loaders.Any(l => l.TryParseSound(stream, out sound)))
						return "no loader reads it";

					using (sound)
					{
						var pcm = sound.GetPCMInputStream();
						var buffer = new byte[65536];
						while (pcm.Read(buffer, 0, buffer.Length) > 0) { }
					}

					return null;
				});

				string problem;
				try
				{
					problem = work.Wait(TimeSpan.FromSeconds(10)) ? work.Result : "hangs (no end after 10 s)";
				}
				catch (AggregateException e)
				{
					problem = e.InnerException?.Message ?? e.Message;
				}

				if (problem != null)
				{
					bad++;
					Console.WriteLine($"{Path.GetFileName(file)}: {problem}");
				}
			}

			Console.WriteLine($"{files.Count} sounds checked, {bad} bad");
			if (bad > 0)
				Environment.Exit(1);
		}
	}
}
