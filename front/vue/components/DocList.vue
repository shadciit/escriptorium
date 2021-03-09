<template>
        <div class="col-12 col-sm-8 col-md-9 col-lg-10 col-md-offset-4">
        <table class="table table-hover">
          <tbody>
            <tr v-for="document in object_list" :key="document.pk">
              <td style="width: 120px;">
                <img v-bind:src="document.part" style="width: 50%;">
              </td>

              <th>
                {{ document.name }}
                <br><span v-if="document.name" class="text-muted"><small>{{ document.typology }}</small></span>
              </th>
              <td>
                <span title="Owner">{{document.owner}}</span>
                <br>
                <span title="Shared with" class="text-muted"><small>{{document.shared}}</small></span>
              </td>
              <td title="Last modified on"><span class="text-muted"><small>{{ document.modif}}</small></span></td>
              <td>
                {{ document.partcount }} image(s).
              </td>
              <td v-html="formattag(document.tags)">
              </td>
              <td class="text-right">
                <a v-bind:href="'/document/' + document.pk +'/edit/'" class="btn btn-info" title="Edit"><i class="fas fa-edit"></i></a>
                <a href="#" v-bind:name="document.pk" title="Assign tag" class="btn btn-info set-tag-meta btn-primary" data-toggle="modal" data-target="#tagAssignModal" v-on:click="launchmodal(document.pk)"><i class="fas fa fa-tags"></i></a>
                <a href="#" v-bind:name="document.pk" title="Remove tag" class="btn btn-info remove-tag-meta btn-danger" v-on:click="launchmodalunassign(document.pk)"><i class="fas fa fa-tag"></i></a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

</template>

<script>

export default {
    computed: {
      object_list() {
        return this.$store.state.documentslist.documents
      },
      baseurl(){
        return this.$store.state.documentslist.basehosturl
      }
    },
    methods: {
        async launchmodal(idd){
              this.$store.commit('documentslist/setDocumentID', idd);
              await this.$store.dispatch('documentslist/getunlinktagbydocument', idd);
             },
        async launchmodalunassign(idd){
            $('#docidrmv').val(idd);
            $('#multiple-checkboxes').multiselect('destroy');
            this.$store.commit('documentslist/setDocumentID', idd);
            await this.$store.dispatch('documentslist/gettagbydocumentrm', this.$store.state.documentslist.documentID);
            setTimeout(() => {
                $('#multiple-checkboxes').multiselect({
                    includeSelectAllOption: true,
                    onChange: function(element, checked) {
                      let brands = $('#multiple-checkboxes option:selected');
                      let selected = [];
                      $(brands).each(function(index, brand){
                          selected.push([$(this).val()]);
                      });
                      $('#selectedtags').val(selected.join(','));
                    }
                });
                $("#tagRemoveModal").modal('show');
            }, 1000);
        },
        formattag(val){
            let listtags = "";
            let dictcolors = {'5': 'danger','4': 'warning','3': 'light','2': 'secondary','1': 'dark'};
            val.split(',').forEach(function(item){
              listtags += '<span class="badge badge-pill badge-'+dictcolors[item.split('¤')[1]]+'">'+item.split('¤')[0]+'</span>'
            });
            return listtags;
        }
    }
    
}
</script>

<style scoped>
.table-hover td 
{
    text-align: center; 
    vertical-align: middle;
}
</style>