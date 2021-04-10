import json
import os
import shutil
import time
from datetime import datetime


class GameInfo:
    def __init__(self, obj):
        self.game_version = obj["gameversion"]
        self.game_build = obj["build"]
        self.language = obj["language"]
        self.part = obj["part"]


class SaveInfo:
    def __init__(self, obj):
        self.username = obj["Commander"]
        self.ship_type = obj.get("Ship_Localised", obj["Ship"].title())
        self.ship_name = obj["ShipName"]
        self.ship_reg = obj["ShipIdent"]
        self.credits = obj["Credits"]


class Bounty:
    def __init__(self, obj):
        self.target_ship = obj.get("Target_Localised", obj["Target"].title())
        self.victim_faction = obj["VictimFaction"]
        self.total_reward = obj["TotalReward"]


class MassacreMission:
    def __init__(self, obj, current_kills=0):
        if obj["Name"] == "Mission_MassacreWing" or obj["Name"] == "Mission_Massacre":
            self.source_faction = obj["Faction"]
            self.target_faction = obj["TargetFaction"]
            self.kill_goal = obj["KillCount"]
            self.reward = obj["Reward"]
            self.is_wing = obj["Wing"]
            self.collected_at = parse_timestamp(obj["timestamp"])
            self.expiry = parse_timestamp(obj["Expiry"])
            self.current_kills = current_kills
        else:
            raise ValueError("Mission is not a massacre mission")


class MissionLog:
    def __init__(self):
        self.active_missions = []
        self.completed_missions = []
        self.current_kills = 0
        self.current_target_kills = 0
        self.total_bounties = 0
        self.target_faction = ""

    def new_mission(self, mission):
        if self.target_faction == "":
            self.target_faction = mission.target_faction

        if mission.target_faction != self.target_faction:
            raise ValueError("New mission's target faction does not match the rest")

        self.active_missions.append(mission)
        self.active_missions.sort(key=lambda x: (x.source_faction, x.collected_at)) # Sort the list by source faction and then by collection time
        # TODO: Is the sort for collected_at in the correct order?

    def new_kill(self, bounty):
        if bounty.victim_faction == self.target_faction: # If the victim's faction is the target faction, count the kill towards missions
            faction_check = [] # List to make sure we are only counting the kill once for each faction
            for mission in self.active_missions:
                    if mission.source_faction not in faction_check: # Check we aren't counting kills that don't stack
                        mission.current_kills += 1
                        faction_check.append(mission.source_faction) # Add the faction to the list to stop the kill being counted towards other missions for the same faction
                        if mission.current_kills == mission.kill_goal: # If we have reached the kill goal, move the mission from active_missions to completed_missions
                            self.completed_missions.append(mission)
                            self.active_missions.remove(mission)
            self.current_target_kills += 1 # TODO: Weirdness with this
        self.total_bounties += bounty.total_reward
        self.current_kills += 1

    def get_unique_factions(self):
        all_missions = self.active_missions + self.completed_missions
        factions = [mission.source_faction for mission in all_missions]
        facitons_unique = list(set(factions))
        facitons_unique.sort()
        return facitons_unique

    def get_required_kills(self):
        kills_by_faction = {}
        all_missions = self.active_missions + self.completed_missions
        for mission in all_missions:
            kills_by_faction[mission.source_faction] = kills_by_faction.get(mission.source_faction, 0) + mission.kill_goal
        
        max_kills = 0
        for faction in kills_by_faction:
            if kills_by_faction[faction] > max_kills:
                max_kills = kills_by_faction[faction] 
        
        return max_kills


def parse_timestamp(timestamp_str):
    return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")


def draw_screen(save_info, mission_log):
    term_size = shutil.get_terminal_size()
    os.system("cls")
    
    welcome_msg = f"##########     Welcome CMDR {save_info.username}     ##########"
    print(welcome_msg.center(term_size.columns))
    print(f"Source Faction Count: {len(mission_log.get_unique_factions())}")
    print(f"Mission Progress: {len(mission_log.completed_missions)}/{len(mission_log.active_missions + mission_log.completed_missions)}")
    print(f"Mission Kill Progress: {mission_log.current_target_kills}/{mission_log.get_required_kills()}")
    print(f"Mission Reward Progress: {sum([mission.reward for mission in mission_log.completed_missions])} CR/{sum([mission.reward for mission in mission_log.completed_missions] + [mission.reward for mission in mission_log.active_missions])} CR")
    print(f"Total Kills: {mission_log.current_kills}")
    print(f"Total Bounties: {mission_log.total_bounties} CR")
    time.sleep(0.2)


def follow_journal(fp, poll_rate):
    while True:
        line = fp.readline()
        if not line:
            time.sleep(poll_rate)
            continue
        else:
            yield line


def parse_journal_line(line):
    obj = json.loads(line)
    obj_event = obj["event"].lower()

    if obj_event == "fileheader": # FileHeader
        return GameInfo(obj)
    elif obj_event == "loadgame": # LoadGame
        return SaveInfo(obj)
    elif obj_event == "missionaccepted": # MissionAccepted
        return MassacreMission(obj)
    elif obj_event == "bounty": # Bounty
        return Bounty(obj)
    elif obj_event == "shutdown": # Shutdown
        return "shutdown"


def main():
    poll_rate = 0.1
    journal_name = "Journal.210408224110.01.log"
    journal_path = os.path.join(os.getenv("homepath"), "Saved Games/Frontier Developments/Elite Dangerous", journal_name)
    
    mission_log = MissionLog()

    try:
        with open(journal_path, "r") as fp:
            journal_lines = follow_journal(fp, poll_rate)
            for line in journal_lines:
                ret = parse_journal_line(line.rstrip())
                if ret: # If the journal line was an event we care about, handle it accordingly
                    if isinstance(ret, GameInfo):
                        game_info = ret
                    elif isinstance(ret, SaveInfo):
                        save_info = ret
                        draw_screen(save_info, mission_log)
                    elif isinstance(ret, MassacreMission):
                        mission_log.new_mission(ret)
                        draw_screen(save_info, mission_log)
                    elif isinstance(ret, Bounty):
                        mission_log.new_kill(ret)
                        draw_screen(save_info, mission_log)
                    elif ret == "shutdown": # DEBUG
                        print("EOF")
                    else:
                        pass
                    
    except IOError:
        print("Error opening journal file!")

    except KeyboardInterrupt:
        print("\nExiting...\n")


if __name__ == "__main__":
    main()