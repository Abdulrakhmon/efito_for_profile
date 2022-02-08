$(document).ready(function(){
    var counter = 2;
    $("#addButton").click(function () {

	if(counter>10){
            alert("Only 10 textboxes allow");
            return false;
	}

	var newTextBoxDiv = $(document.createElement('div'))
	     .attr("id", 'dynamic_div_' + counter);
	newTextBoxDiv.after().html(`<div class="row">
                                                    <div class="col-5">
                                                        <input name="product_name_${counter}" class="form-control" type="text"
                                                               required>
                                                        <br>
                                                    </div>
                                                    <div class="col-5">
                                                        <input name="product_quantity_${counter}" class="form-control"
                                                               type="number"
                                                               required>
                                                    </div>
                                                    <div class="col-2">
                                                        <button type='button' class="btn btn-block btn-danger btn-md" id='removeButton_${counter}'
                                                                onClick="delete_selected(this.id)"><i class="fas fa-minus-circle"> </i></button>
                                                    </div>
                                                </div>`);
	newTextBoxDiv.appendTo("#dynamic_form");
	counter++;
     });
  });
    function delete_selected(selected_div_id){
    selected_div_id = selected_div_id[selected_div_id.length - 1];
	if($("[id*='removeButton_']").length == 1){
          alert("По крайней мере, вы должны добавить один продукт!");
          return false;
       }
    $("#dynamic_div_" + selected_div_id).remove();
    }