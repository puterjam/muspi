#!/usr/bin/env python3
"""
Simple test script for libdiscid and musicbrainzngs
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import musicbrainzngs as mb
import libdiscid
import json

CD_DEVICE = "/dev/sr0"

def test_diskid():
    """Test reading disc ID from CD"""
    print("=" * 60)
    print("Testing libdiscid...")
    print("=" * 60)

    try:
        disc = libdiscid.read(CD_DEVICE)
        print(f"✓ Successfully read disc from {CD_DEVICE}")
        print(f"  Disc ID: {disc.id}")
        print(f"  TOC: {disc.toc}")

        # Parse TOC to get track info
        toc_parts = disc.toc.split(' ')
        first_track = int(toc_parts[0])
        last_track = int(toc_parts[1])
        track_count = last_track - first_track + 1

        print(f"  Track count: {track_count}")
        print(f"  First track: {first_track}")
        print(f"  Last track: {last_track}")

        return disc

    except Exception as e:
        print(f"✗ Error reading disc: {e}")
        return None


def test_musicbrainz(disc):
    """Test querying MusicBrainz for disc info"""
    if disc is None:
        print("\n⊘ Skipping MusicBrainz test (no disc available)")
        return

    print("\n" + "=" * 60)
    print("Testing MusicBrainz query...")
    print("=" * 60)

    try:
        # Set user agent for MusicBrainz
        mb.set_useragent('muspi', '1.0', 'https://github.com/puterjam/muspi')

        print(f"  Querying MusicBrainz for disc ID: {disc.id}")
        result = mb.get_releases_by_discid(
            disc.id,
            includes=["recordings", "artists"],
            cdstubs=False
        )

        print(f"✓ Successfully retrieved data from MusicBrainz")

        # Parse and display the results
        if 'disc' in result and 'release-list' in result['disc']:
            releases = result['disc']['release-list']
            print(f"  Found {len(releases)} release(s)")

            for i, release in enumerate(releases, 1):
                print(f"\n  Release #{i}:")
                print(f"    Title: {release.get('title', 'Unknown')}")
                print(f"    Artist: {release.get('artist-credit-phrase', 'Unknown')}")

                if 'medium-list' in release:
                    for medium in release['medium-list']:
                        if 'track-list' in medium:
                            print(f"    Tracks: {len(medium['track-list'])}")
                            print(f"    Track list:")
                            for j, track in enumerate(medium['track-list'][:5], 1):  # Show first 5 tracks
                                track_title = track.get('recording', {}).get('title', 'Unknown')
                                print(f"      {j}. {track_title}")
                            if len(medium['track-list']) > 5:
                                print(f"      ... and {len(medium['track-list']) - 5} more tracks")

        # Save to file
        os.makedirs("config/cd", exist_ok=True)
        save_path = f"config/cd/{disc.id}.json"
        with open(save_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n  ✓ Saved to: {save_path}")

        return result

    except mb.ResponseError as e:
        print(f"✗ MusicBrainz API error: {e}")
        return None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\nCD Disc ID and MusicBrainz Test\n")

    # Test 1: Read disc ID
    disc = test_diskid()

    # Test 2: Query MusicBrainz
    test_musicbrainz(disc)

    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
