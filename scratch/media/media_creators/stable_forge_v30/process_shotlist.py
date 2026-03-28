from tangl.config import settings
from tangl.world.illustrator.stableforge import StableForge

SHOTLIST_FILE = 'shotlist.yaml'
SHOW_IMS = True

if __name__ == "__main__":

    forge = StableForge('default', apis=settings.stableforge.workers)
    shots = forge.load_shotlist(fp=SHOTLIST_FILE)
    print( shots )
    print( len(shots) )

    if SHOW_IMS:
        for s in shots[4::20]:
            if not s.uid.startswith("id-photo"):
                continue
            img = forge.spec2img(s)
            print( s.uid )
            img.show()
