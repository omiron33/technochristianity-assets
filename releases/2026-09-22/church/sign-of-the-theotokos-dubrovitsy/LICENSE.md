# Provenance

`source.jpg` is retained in the authoring project as a reconstruction reference
for Technochristian.
Procedural geometry was created for this repository. Retained photographs,
projected image fields, and historical drawings retain the individual licenses
and attributions in this release's `credits.json`, `photographic-provenance.json`
and `textures/provenance.json`.
The photo records distinguish CC BY-SA 3.0, CC BY-SA 4.0, public-domain material,
and reconstruction references; those sources are not relicensed as original
repository materials. Parish and encyclopedia URLs identify architectural descriptions.

The exterior uses credited photographs by **Okorok** for the retained Sign02
elevation and legacy lobe, rustication and statue selections, and **Mike1979
Russia** for the 2024 upper-tower photograph. These sources retain their
**CC BY-SA 3.0** attribution and share-alike terms. Okorok's 2005 Sign31 tower
photograph is an architectural comparison only; it is not currently projected.
The legacy crown photograph by **Додонов Вячеслав Николаевич** and its retained
derivatives keep their separate CC BY-SA 3.0 record. Source URLs and exact
retained-byte identities are recorded in the photographic provenance files.

Exterior calibration applies gamma, saturation and linear gain to six authored
materials without creating new raster files: 0.74 / 0.12 / 1.3 for the 2024 tower
source, and 0.76 / 0.38 / 1.15 for full Sign02 and the retained lobe, rustication
and two statue derivatives. This is an artistic albedo approximation, not a
measurement of the church's reflectance. The original source, a historical
crop/resample and a material adjustment remain distinct in the records.
Modeled cornices, parapets, figures and relief depth are interpretive adaptations;
their construction does not remove the photographic sources' license terms.

The park's generated terrain, ground grain, leaf cutouts and tree geometry are
procedural work produced by `scripts/church/dubrovitsy-site.py`. The aerial
reference guides their broad arrangement; these assets are not scans of the
actual grounds. The separately licensed material maps below supply only their
documented church surfaces.

The floor uses [Marble 01](https://polyhaven.com/a/marble_01) by **Rob Tuytel**,
provided by Poly Haven under [CC0](https://polyhaven.com/license). Original
4096 × 4096 diffuse and OpenGL normal-map JPEGs are included among the model
textures; their hashes, source URLs, sampling and material adjustments are
recorded in `photographic-provenance.json`. The authoring project also retains
a roughness image that is not used by this floor material or included here.
This generic stone sample supplies veins
and surface response; it is not a photograph or scan of the church floor.
Its auxiliary credit is excluded from the church-photograph gallery.

The painted plaster finish uses [White Plaster 02](https://polyhaven.com/a/white_plaster_02)
by **Rob Tuytel**, also supplied by Poly Haven under CC0. Original 1k OpenGL normal
and packed ARM JPEGs provide fine surface response at a 1 m repeat. The ARM
green channel supplies roughness; red AO is unused and blue metallic has a zero
factor. Authored blue and chalk base colors are preserved. The diffuse and
standalone roughness originals are retained in the authoring project but unused
and not included here. Source URLs, original
hashes, dimensions and the source's scale discrepancy are
recorded in `photographic-provenance.json`. This is a generic material sample,
not a photograph or survey of Dubrovitsy plaster. Its material entry in
`photographic-provenance.json` distinguishes used maps from retained originals;
the auxiliary material credit is excluded from the church-photograph gallery.

Full-image source records and the Poly Haven maps retain their original bytes.
The recovered cropped/resampled church textures are identified separately in
`textures/provenance.json`; they are not covered by a blanket unchanged-original
claim. Projective UVs, modeled relief and material gamma, saturation, linear gain,
normal strength and roughness adjustments determine the reconstructed appearance
without relicensing the underlying photographs. These asset notices do not
change the repository's code license.

This runtime release contains the glTF model, geometry buffers, model textures
and attribution documents. It does not include the editable Blender scene,
authoring scripts or source-archive restore files. Their omission does not change
the attribution or license terms of the photographs, retained derivatives and
material maps included in the runtime model.
