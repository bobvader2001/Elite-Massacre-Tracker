import json
import os
import time


class MassacreMission:
    def __init__(self, obj):
        if obj["Name"] == "Mission_MassacreWing" or obj["Name"] == "Mission_Massacre":
            self.source_faction = obj["Faction"]
            self.target_faction = obj["TargetFaction"]
            self.kill_count = obj["KillCount"]
            self.reward = obj["Reward"]
            self.is_wing = obj["Wing"]
            self.collected_at = obj["timestamp"] # TODO: Make datetime
            self.expiry = obj["Expiry"] # TODO: Make datetime
        else:
            raise ValueError("Mission is not a massacre mission")


def follow_journal(fp, poll_rate):
    while True:
        line = fp.readline()
        if not line:
            time.sleep(poll_rate)
            continue
        else:
            yield line


def parse_journal_line(line, mission_log):
    obj = json.loads(line)
    obj_event = obj["event"].lower()

    if obj_event == "fileheader": # FileHeader
        print(f"Game Version: {obj['gameversion']}")
        print(f"Game Build: {obj['build']}")
        print(f"Language: {obj['language']}")
    if obj_event == "commander": # Commander
        print(f"\n##### Welcome CMDR {obj['Name']} ({obj['FID']}) #####\n")
    if obj_event == "loadgame": # LoadGame
        print(f"Ship Name: {obj['ShipName']}")
        print(f"Ship Type: {obj['Ship_Localised']}")
        print()
    if obj_event == "missionaccepted": # MissionAccepted
        new_mission = MassacreMission(obj)
        mission_log.append(new_mission)
        return True


def main():
    poll_rate = 0.1
    journal_name = "Journal.210408224110.01.log"
    journal_path = os.path.join(os.getenv("homepath"), "Saved Games/Frontier Developments/Elite Dangerous", journal_name)
    
    mission_log = []

    try:
        with open(journal_path, "r") as fp:
            journal_lines = follow_journal(fp, poll_rate)
            for line in journal_lines:
                if parse_journal_line(line.rstrip(), mission_log):
                    print("-- New Mission Accepted --")
                    print(f"\tSource: {mission_log[-1].source_faction}")
                    print(f"\tTarget: {mission_log[-1].target_faction}")
                    print(f"\tKill Count: {mission_log[-1].kill_count}")
                    print(f"\tReward: {mission_log[-1].reward}")
                    print()
                    
    except IOError:
        print("Error opening journal file!")

    except KeyboardInterrupt:
        print("\nExiting...\n")


if __name__ == "__main__":
    main()