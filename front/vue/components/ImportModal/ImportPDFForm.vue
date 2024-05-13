<template>
    <div>
        <h3>Import images from a PDF document</h3>
        <span>Import images by uploading a single PDF with one image per page.</span>
        <fieldset class="pdf-import">
            <input
                type="file"
                accept=".pdf"
                :class="{ invalid: invalid['file'] }"
                @change="handleFileChange"
            >
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

export default {
    name: "EscrImportPDFForm",
    props: {
        invalid: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapState({
            partsCount: (state) => state.document.partsCount,
            position: (state) => state.forms.import.position,
        })
    },
    methods: {
        ...mapActions("forms", [
            "handleGenericInput",
        ]),
        handleFileChange(e) {
            this.handleGenericInput({
                form: "import",
                field: "uploadFile",
                value: e.target.files[0],
            });
        },
        handlePositionChange(e) {
            this.handleGenericInput({
                form: "import", field: "position", value: e.target.value,
            });
        },
    }
}
</script>
