<template>
    <div>
        <h3>Import images from IIIF</h3>
        Input a valid IIIF manifest URI to import all of its images in full resolution
        along with its metadata.
        <fieldset>
            <TextField
                label="IIIF Manifest URI"
                placeholder="https://gallica.bnf.fr/iiif/ark:/12148/btv1b10224708f/manifest.json"
                :invalid="invalid['iiifUri']"
                :on-input="handleIIIFInput"
                :value="iiifUri"
                :max-length="255"
            />
        </fieldset>
        <fieldset v-if="partsCount > 0">
            <label class="escr-text-field escr-form-field img-position-field">
                <span
                    class="escr-field-label"
                >
                    Import to position (optional):
                </span>
                <input
                    type="number"
                    step="1"
                    min="0"
                    :max="partsCount"
                    :placeholder="`Enter number from 0–${partsCount}`"
                    :value="position"
                    @change="handlePositionChange"
                >
            </label>
        </fieldset>
    </div>
</template>
<script>
import { mapActions, mapState } from "vuex";
import TextField from "../TextField/TextField.vue";

export default {
    name: "EscrImportIIIFForm",
    components: { TextField },
    props: {
        invalid: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapState({
            iiifUri: (state) => state.forms.import.iiifUri,
            partsCount: (state) => state.document.partsCount,
            position: (state) => state.forms.import.position,
        })
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        handleIIIFInput(e) {
            this.handleGenericInput({
                form: "import",
                field: "iiifUri",
                value: e.target.value,
            });
        },
        handlePositionChange(e) {
            this.handleGenericInput({
                form: "import", field: "position", value: e.target.value,
            });
        },
    },
}
</script>
