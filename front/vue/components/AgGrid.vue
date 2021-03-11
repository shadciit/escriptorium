<template>
    <div class="col-12 col-sm-8 col-md-9 col-lg-10 col-md-offset-4">
        <aggrid-vue style="width: 100%; height: 800px;"
            class="ag-theme-alpine"
            :columnDefs="columnDefs"
            :rowData="rowData"
            :gridOptions="gridOptions"
            :defaultColDef="defaultColDef"
            :modules="modules"
            :rowSelection="'multiple'"
        >
        </aggrid-vue>
    </div>
</template>

<script>
    import { AllCommunityModules } from '@ag-grid-community/all-modules';
    import { AgGridVue } from "@ag-grid-community/vue";
    import Assigntg from './renderer/Assigntg.vue';
    import Unassigntg from './renderer/Unassigntg.vue';
    import Editdocument from './renderer/Editdocument.vue';

    export default {
        name: 'AgGrid',
        data() {
            return {
                gridApi: null,
                gridOptions: null,
                columnDefs: null,
                rowData: null,
                defaultColDef: null,
                modules: AllCommunityModules
            }
        },
        components: {
            'aggrid-vue': AgGridVue,
            'assigntg': Assigntg,
            'unassigntg': Unassigntg,
            'editdocument': Editdocument
        },
        beforeMount() {
            this.gridOptions = {rowHeight: 100, headerHeight: 30, enableRangeSelection: true, pagination: true, suppressCellSelection: true};
            this.columnDefs = [
                { headerName: '', field: 'part_image', filter: false, checkboxSelection: true, cellRenderer: params => '<img src="' + params.value + '" style="width: 50%;">'},
                { headerName: '', field: 'name', width: 250, editable: true, sortable: true, filter: true, sortable: true, cellStyle: { 'margin-top': "2%" }},
                { headerName: '', field: 'owner', cellStyle: { 'margin-top': "2%" }},
                { headerName: '', field: 'updated_at', sortable: true, cellStyle: { 'margin-top': "2%" }}, 
                { headerName: '', field: 'part_count', cellRenderer: params => params.value > 1 ? params.value + " images." : params.value + " image."},
                { headerName: '', field: 'tags', filter: false, cellStyle: { 'margin-top': "2%" }, width: 270, cellRenderer: params => this.formattag(params.value) },
                { headerName: '', field: 'pk', filter: false, width: 80, cellRendererFramework: 'editdocument', cellStyle: { 'margin-top': "2%" }},
                { headerName: '', field: 'pk', filter: false, width: 90, cellRendererFramework: 'assigntg', cellStyle: { 'margin-top': "2%" }},
                { headerName: '', field: 'pk', filter: false, width: 80, cellRendererFramework: 'unassigntg', cellStyle: { 'margin-top': "2%" }, suppressNavigable: true, cellClass: 'no-border'}
            ];
            this.defaultColDef = {
                width: 150,
                editable: false,
                filter: 'agTextColumnFilter',
                floatingFilter: true,
                resizable: true,
                suppressNavigable: true,
                cellClass: 'no-border'
            };
        },
        mounted() {
            this.gridOptions.api.setDomLayout('autoHeight');
            this.gridApi = this.gridOptions.api;
            this.gridColumnApi = this.gridOptions.columnApi;
        },
        methods: {
            formattag(val){
                let listtags = "";
                let dictcolors = {'5': 'danger','4': 'warning','3': 'light','2': 'secondary','1': 'dark'};
                val.split(',').forEach(function(item){
                    listtags += '<span class="badge badge-pill badge-'+dictcolors[item.split('¤')[1]]+'">'+item.split('¤')[0]+'</span>'
                });
                return listtags;
            },
        },
        watch: {
            "$store.state.documentslist.documents": {
            handler: function(nv) {
                this.rowData = nv
            },
            immediate: true 
            }
        }
    };
</script>


<style scoped>
    .ag-cell-focus,.ag-cell-no-focus{
        border:none !important;
    }
    .no-border.ag-cell:focus{
        border:none !important;
        outline: none;
    }
</style>


