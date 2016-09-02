function vital = parseVitalFile(szVitalFile)
%
% This function is used to parse the Vital file.
% The format of vital file is as follows:
%       Header
%       Body
% Input:
%   szVitalFile: The name of vital sign file (binary file)
% Author: Yong Bai 10/29/2013

fp = fopen(szVitalFile, 'rb');

name = fread(fp, 16, 'char');
vital.name = char (name');

uom = fread(fp,  8, 'char');
vital.uom  = char(uom');

unit = fread(fp,  8, 'char');
vital.unit = char(unit');

bed = fread(fp,  4, 'char');
vital.bed = char(bed');

year = fread(fp,1, 'int');
vital.startyear = year;

month = fread(fp,1, 'int');
vital.startmonth = month;

day = fread(fp,1, 'int');
vital.startday = day;

hour = fread(fp,1, 'int');
vital.starthour = hour;

minute = fread(fp,1, 'int');
vital.startminute = minute;

seconds = fread(fp,1, 'double');
vital.startsecond = seconds;

data = fread(fp,  inf, 'double');

fclose(fp);
numData = length(data);
data = reshape(data, 4, numData/4);
vital.value = data(1,:);
vital.offset  = data(2,:);
vital.limitLo = data(3,:);
vital.limitHi = data(4,:);

%plot(data(2,:)/1000/60/60/24, data(1,:))
