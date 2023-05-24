// Utility to store the initial state for each form, so that forms can easily be cleared by key/name

export default {
    align: {
        beamSize: "",
        gap: 600,
        layerName: "",
        maxOffset: "",
        merge: false,
        ngram: 25,
        overwriteWarningVisible: false,
        regionTypes: [],
        showAdvanced: false,
        threshold: 0.8,
        textualWitness: "",
        textualWitnessFile: null,
        textualWitnessType: "select",
        tooltipShown: {
            beamSize: false,
            gap: false,
            maxOffset: false,
            ngram: false,
            threshold: false,
        },
        transcription: "",
        fullDoc: false,
    },
    editDocument: {
        linePosition: "",
        mainScript: "",
        metadata: [],
        name: "",
        readDirection: "",
        tags: [],
        tagName: "",
    },
    editProject: {
        guidelines: "",
        name: "",
        tags: [],
        tagName: "",
    },
    segment: {
        model: "",
        overwrite: false,
        include: [],
        textDirection: "",
    },
    share: {
        group: "",
        user: "",
    },
    transcribe: {
        model: "",
        layerName: "",
    },
};
