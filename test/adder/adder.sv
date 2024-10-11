module adder # (
    parameter  N_DATA = 8
)(
    input  logic [N_DATA-1:0]   i_a ,
    input  logic [N_DATA-1:0]   i_b ,
    output logic [N_DATA+1-1:0] o_c 
);
    assign o_c = i_a + i_b;
endmodule