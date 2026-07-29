from pathlib import Path

CFG_DIR = Path("~/.dexmate/comm/zenoh").expanduser()
ZENOH_TC_PORT = 7447


def setup_zenoh_config() -> tuple[Path, Path]:
    """Write router and client configs and return (router_cfg, client_cfg).

    The simulation runs as the Zenoh router on ZENOH_TC_PORT.
    dexcontrol and any other participant connect as clients.
    Router/client over TCP is deterministic — no multicast, no discovery delay.
    """
    CFG_DIR.mkdir(parents=True, exist_ok=True)

    addr = f"tcp/127.0.0.1:{ZENOH_TC_PORT}"
    router_cfg = CFG_DIR / "bridge.json5"
    client_cfg = CFG_DIR / "client.json5"

    router_cfg.write_text(
        f'{{\n  mode: "router",\n  listen: {{ endpoints: ["{addr}"] }}\n}}\n'
    )
    client_cfg.write_text(
        f'{{\n  mode: "client",\n  connect: {{ endpoints: ["{addr}"] }}\n}}\n'
    )

    return router_cfg, client_cfg
