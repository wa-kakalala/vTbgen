#! /usr/bin/env python

'''
vTbgenerator.py -- generate verilog module Testbench
generated bench file like this:

        fifo_sc #(
            .DATA_WIDTH ( 8 ),
            .ADDR_WIDTH ( 8 )
        )
         u_fifo_sc (
            .CLK   ( CLK                     ),
            .RST_N ( RST_N                   ),
            .RD_EN ( RD_EN                   ),
            .WR_EN ( WR_EN                   ),
            .DIN   ( DIN   [DATA_WIDTH-1 :0] ),
            .DOUT  ( DOUT  [DATA_WIDTH-1 :0] ),
            .EMPTY ( EMPTY                   ),
            .FULL  ( FULL                    )
        );

Usage:
      python vTbgenerator.py ModuleFileName.v

'''

import re
import sys
import chardet

def delComment( Text ):
    """ removed comment """
    single_line_comment = re.compile(r"//(.*)$", re.MULTILINE)
    multi_line_comment  = re.compile(r"/\*(.*?)\*/",re.DOTALL)
    Text = multi_line_comment.sub('\n',Text)
    Text = single_line_comment.sub('\n',Text)
    return Text

def delBlock( Text ) :
    """ removed task and function block """
    Text = re.sub(r'\Wtask\W[\W\w]*?\Wendtask\W','\n',Text)
    Text = re.sub(r'\Wfunction\W[\W\w]*?\Wendfunction\W','\n',Text)
    return Text

def findName(inText):
    """ find module name and port list"""
    p = re.search(r'([a-zA-Z_][a-zA-Z_0-9]*)\s*',inText)
    mo_Name = p.group(0).strip()
    return mo_Name

def paraDeclare(inText ,portArr) :
    """ find parameter declare """
    pat = r'\s'+ portArr + r'\s[\w\W]*?[;,)]'
    ParaList = re.findall(pat ,inText)

    return ParaList

def portDeclare(inText ,portArr) :
    """find port declare, Syntax:
       input [ net_type ] [ signed ] [ range ] list_of_port_identifiers

       return list as : (port, [range])
    """
    port_definition = re.compile(
        r'\b' + portArr +
        r''' (\s+(wire|reg|logic)\s+)* (\s*signed\s+)*  (\s*\[.*?:.*?\]\s*)*
        (?P<port_list>.*?)
        (?= \binput\b | \boutput\b | \binout\b | ; | \) )
        ''',
        re.VERBOSE|re.MULTILINE|re.DOTALL
    )

    pList = port_definition.findall(inText)

    t = []
    for ls in pList:
        if len(ls) >=2  :
            t = t+ portDic(ls[-2:])
    return t

def portDic(port) :
    """delet as : input a =c &d;
        return list as : (port, [range])
    """
    pRe = re.compile(r'(.*?)\s*=.*', re.DOTALL)

    pRange = port[0]
    pList  = port[1].split(',')
    pList  = [ i.strip() for i in pList if i.strip() !='' ]
    pList  = [(pRe.sub(r'\1', p), pRange.strip() ) for p in pList ]

    return pList

def formatPort(AllPortList,isPortRange =1) :
    PortList = AllPortList[0] + AllPortList[1] + AllPortList[2]

    str =''
    if PortList !=[] :
        l1 = max([len(i[0]) for i in PortList])+2
        l2 = max([len(i[1]) for i in PortList])
        l3 = max(24, l1)

        strList = []
        for pl in AllPortList :
            if pl  != [] :
                str = ',\n'.join( [' '*4+'.'+ i[0].ljust(l3)
                                  + '( '+ (i[0].ljust(l1 )+i[1].ljust(l2))
                                  + ' )' for i in pl ] )
                strList = strList + [ str ]

        str = ',\n\n'.join(strList)

    return str

def formatDeclare(PortList,portArr, initial = "" ):
    str =''
    if initial !="" :
        initial = " = " + initial

    if PortList!=[] :
        str = '\n'.join( [ portArr.ljust(4) +'  '+(i[1]+min(len(i[1]),1)*'  '
                           +i[0]).ljust(36)+ initial + ' ;' for i in PortList])
    return str

def formatPara(ParaList) :
    paraDec = ''
    paraDef = ''
    if ParaList !=[]:
        s = '\n'.join( ParaList)
        pat = r'([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*([\w\W]*?)\s*[;,)]'
        p = re.findall(pat,s)

        l1 = max([len(i[0] ) for i in p])
        l2 = max([len(i[1] ) for i in p])
        paraDec = '\n'.join( ['parameter %s = %s;'
                             %(i[0].ljust(l1 +1),i[1].ljust(l2 ))
                             for i in p])
        paraDef =  '#(\n' +',\n'.join( ['    .'+ i[0].ljust(l1 +1)
                    + '( '+ i[0].ljust(l1 )+' )' for i in p])+ '\n)'
    else:
        l1 = 6
        l2 = 2
    preDec = '\n'.join( ['parameter %s = %s;\n'
                             %('PERIOD'.ljust(l1 +1), '10'.ljust(l2 ))])
    paraTimout = '\n'.join( ['parameter %s = %s;\n'
                             %('TIMEOUT'.ljust(l1 +1), '100000000'.ljust(l2 ))])
    paraDec = preDec + paraTimout + paraDec
    return paraDec,paraDef

def getClkRstName(InputList):
    clk_name,rst_name= 'clk','rst_n'
    clk_exist,rst_exist = 0,0
    for in_port in InputList:
        if "clk" in in_port or "CLK" in in_port:
            clk_name = in_port
            break

    for in_port in InputList:
        if "rst" in in_port or "RST" in in_port:
            rst_name = in_port
            break
    return clk_name,rst_name,clk_exist,rst_exist

def writeTestBench(input_file):
    """ write testbench to file """
    with open(input_file, 'rb') as f:
        f_info =  chardet.detect(f.read())
        f_encoding = f_info['encoding']
    with open(input_file, encoding=f_encoding) as inFile:
        inText  = inFile.read()

    # removed comment,task,function
    inText = delComment(inText)
    inText = delBlock  (inText)

    # moduel ... endmodule  #
    moPos_begin = re.search(r'(\b|^)module\b', inText ).end()
    moPos_end   = re.search(r'\bendmodule\b', inText ).start()
    inText = inText[moPos_begin:moPos_end]

    name  = findName(inText)
    paraList = paraDeclare(inText,'parameter')
    paraDec , paraDef = formatPara(paraList)

    ioPadAttr = [ 'input','output','inout']
    input  =  portDeclare(inText,ioPadAttr[0])
    output =  portDeclare(inText,ioPadAttr[1])
    inout  =  portDeclare(inText,ioPadAttr[2])

    clk_name,rst_name,clk_exist,rst_exist = getClkRstName(input) 

    # if not clk_exist:
    #     input = [('clk','') ] + input
    # if not rst_exist:
    #     input = [('rst_n','') ] + input
    portList = formatPort( [input , output , inout] )
    # input  = formatDeclare(input ,'reg', '0' )
    # output = formatDeclare(output ,'wire')
    # inout  = formatDeclare(inout ,'wire')
    input  = formatDeclare(input ,'logic', '0' )
    output = formatDeclare(output ,'logic')
    inout  = formatDeclare(inout ,'logic')

    # if clk_exist == 0 :

    # if rst_exist == 0:


    # write testbench
    timescale = '`timescale  1ns / 1ps\n'
    print("//~ `New testbench")
    print(timescale)
    print("module tb_%s;\n" % name)

    # module_parameter_port_list
    if(paraDec!=''):
        print("// %s Parameters\n%s\n" % (name, paraDec))
    # list_of_port_declarations
    print("// %s Inputs\n%s\n"  % (name, input ))
    print("// %s Outputs\n%s\n" % (name, output))
    if(inout!=''):
        print("// %s Bidirs\n%s\n"  % (name, inout ))

    # print clock
    clk = '''
initial begin
    forever #(PERIOD/2)  %s=~%s;
end'''%(clk_name,clk_name)

    rst = '''
initial begin
    #(PERIOD*2) %s  <=  1'b1;
end
'''%(rst_name)
    
    timeout = '''
int cnt = 0;
initial begin
    forever begin : timeout_block
        @(posedge %s);
        cnt += 1;
        if( cnt > TIMEOUT ) begin
            $display("timeout exception !!!");
            disable timeout_block;
        end
    end
end
'''%(clk_name)

    print("%s\n%s\n%s" % (clk,rst,timeout))
    # UUT
    print("%s %s %s_inst (\n%s\n);" %(name,paraDef,name,portList))
    
    #  construct data
    constructor = '''
int tran_queue[$];
int result_queue[$];
int expect_queue[$];
initial begin
    // add data to tran_queue and expect_queue
end
'''
    print("%s"%(constructor))
    # checker
    checker = '''
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
'''
    print("%s"%(checker))
    operation = '''
initial begin
    wait(%s == 1'b1 );
    @(posedge %s);
    // driver code  

    ->chk_event;
    #(PERIOD);
    $stop;
end
'''%(rst_name,clk_name)
    # print operation
    print(operation)
    print("endmodule")

if __name__ == '__main__':
    writeTestBench(sys.argv[1])
