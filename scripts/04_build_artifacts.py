from psl.artifacts.figures import write_all
from psl.artifacts.passports import write_passports
from psl.artifacts.manifest import build_manifest, build_model_cards
from psl.artifacts.relationships import attach_relationships
from psl.site.build import build_site

if __name__ == "__main__":
    attach_relationships()
    write_all()
    write_passports()
    build_manifest()
    build_model_cards()
    build_site()
    print("artifacts + site written")
