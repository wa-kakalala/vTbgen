//~ `New testbench
`timescale  1ns / 1ps

module tb_adder;

// adder Parameters
parameter PERIOD  = 10;
parameter TIMEOUT = 100000000;
parameter N_DATA  = 8;

// adder Inputs
logic  [N_DATA-1:0]  i_a                    = 0 ;
logic  [N_DATA-1:0]  i_b                    = 0 ;

logic  clk = 0;
logic  rst_n = 0;

// adder Outputs
logic  [N_DATA+1-1:0]  o_c                  ;


initial begin
    forever #(PERIOD/2)  clk=~clk;
end

initial begin
    #(PERIOD*2) rst_n  <=  1'b1;
end


int cnt = 0;
initial begin
    forever begin : timeout_detect
        @(posedge clk);
        cnt += 1;
        if( cnt > TIMEOUT ) begin
            $display("timeout exception !!!");
            disable timeout_detect;
        end
    end
end

adder #(
    .N_DATA ( N_DATA )
) adder_inst (
    .i_a                     ( i_a  [N_DATA-1:0]   ),
    .i_b                     ( i_b  [N_DATA-1:0]   ),

    .o_c                     ( o_c  [N_DATA+1-1:0] )
);

int tran_queue[$];
int result_queue[$];
int expect_queue[$];
initial begin
    // add data to tran_queue and expect_queue
end


event chk_event;
bit not_match;
initial begin
    not_match = 0;
    @(chk_event);
    if(  result_queue.size() != expect_queue.size() ) begin
        $display("size not match -> result_queue : %d,expect_queue: %d",result_queue.size(),expect_queue.size());
    end

    foreach(expect_queue[i]) begin
        if( expect_queue[i] !== result_queue[i] ) begin
            not_match = 1;
            $display("**********fail**********");
            break;
        end
    end
    if( not_match == 0 ) begin
        $display("**********pass**********");
    end
end


initial begin
    wait(rst_n == 1'b1 );
    @(posedge clk);
    // driver code

    ->chk_event;
    #(PERIOD);
    $stop;
end

endmodule