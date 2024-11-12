from atproto import Client, models
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from concurrent.futures import ThreadPoolExecutor
import numpy as np

def main():
    login_handle = input("login username: ")
    login_password = input("login password: ")

    client = Client()
    client.login(login_handle, login_password)

    username = input("username: ")
    user_did = client.resolve_handle(username).did
    user_profile = client.get_profile(user_did)

    following_cache = {}
    followers_cache = {}

    def get_followers(did: str):
        if did in followers_cache:
            return followers_cache[did]
        
        follower_dids = []
        cursor = None
        print(f"Fetching followers for {did}...")
        while True:
            followers = client.get_followers(did, cursor=cursor)
            follower_dids.extend(follow['did'] for follow in followers['followers'])
            cursor = followers.cursor
            if not cursor:
                break
        followers_cache[did] = follower_dids
        print(f"Found {len(follower_dids)} followers for {did}.")
        return follower_dids

    def get_following(did: str):
        if did in following_cache:
            return following_cache[did]
        
        follow_dids = []
        cursor = None
        print(f"Fetching following for {did}...")
        while True:
            follows = client.get_follows(did, cursor=cursor)
            follow_dids.extend(follow['did'] for follow in follows['follows'])
            cursor = follows.cursor
            if not cursor:
                break
        following_cache[did] = follow_dids
        print(f"Found {len(follow_dids)} following for {did}.")
        return follow_dids

    def get_mutuals(did: str):
        print(f"Finding mutuals for {did}...")
        followers = set(get_followers(did))
        following = set(get_following(did))
        mutuals = list(followers & following)
        print(f"Found {len(mutuals)} mutuals for {did}.")
        return mutuals

    mutuals = get_mutuals(user_did)

    G = nx.Graph()
    G.add_node(user_did, label=user_profile.display_name)

    def add_mutual_to_graph(mutual):
        print(f"Adding mutual {mutual} to the graph...")
        profile = client.get_profile(mutual)
        display_name = profile.display_name if profile.display_name else mutual
        G.add_node(mutual, label=display_name)
        G.add_edge(user_did, mutual)
        print(f"Mutual {mutual} added to the graph.")

    with ThreadPoolExecutor() as executor:
        print(f"Starting to add mutuals to the graph...")
        executor.map(add_mutual_to_graph, mutuals)
        print(f"Finished adding mutuals to the graph.")

    print(f"Adding edges between mutuals who are mutuals with each other...")
    for i, mutual_a in enumerate(mutuals):
        for mutual_b in mutuals[i + 1:]:
            following_a = set(get_following(mutual_a))
            following_b = set(get_following(mutual_b))

            if mutual_b in following_a and mutual_a in following_b:
                G.add_edge(mutual_a, mutual_b)
                print(f"Added edge between {mutual_a} and {mutual_b}.")

    print("Plotting the graph...")
    pos = nx.spring_layout(G, seed=42, k=.5)
    labels = nx.get_node_attributes(G, 'label')
    plt.figure(figsize=(12, 8))

    degrees = dict(G.degree)
    node_sizes = [2500 + (100 * degrees[node]) for node in G.nodes()]

    MIN_INTENSITY = .3 # When too faint becomes hard to read
    degree_values = np.array(list(degrees.values()))
    norm = plt.Normalize(vmin=degree_values.min(), vmax=degree_values.max())
    node_colors = [cm.Blues(MIN_INTENSITY + (1 - MIN_INTENSITY) * norm(degrees[node])) for node in G.nodes()]

    nx.draw(G, pos, with_labels=True, labels=labels,
            node_size=node_sizes,
            node_color=node_colors, 
            font_size=10, font_weight='bold',
            edge_color='gray', alpha=0.7,
            width=2)
    
    plt.show()

if __name__ == '__main__':
    main()
