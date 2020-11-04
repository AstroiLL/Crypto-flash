// AstroiLL
// 2020

// @version=4

study(title="SMA MTF", shorttitle="SMA MTF", overlay=true)

len1 = input(defval=24, title="SMA #1 length")
len2 = input(defval=30, title="SMA #2 length")
type1 = input(defval="SMA", options=["SMA", "EMA", "VWMA", "RMA"], title="MA Type")
type2 = input(defval="SMA", options=["SMA", "EMA", "VWMA", "RMA"], title="MA Type")
ma1tf = input(type=input.resolution, defval='60', title="SMA #1 Timeframe")
ma2tf = input(type=input.resolution, defval='D', title="SMA #2 Timeframe")

ma1 = security(syminfo.tickerid, ma1tf, sma(close, len1))
ma2 = security(syminfo.tickerid, ma2tf, sma(close, len2))

// MA
// ma1 = type1 == "SMA" ? sma(src1, len): type1 == "EMA" ? ema(src1, len): type1 == "VWMA" ? vwma(src1, len): rma(src1,
                                                                                                                  len)
// ma2 = type2 == "SMA" ? sma(src1, len): type2 == "EMA" ? ema(src1, len): type2 == "VWMA" ? vwma(src1, len): rma(src1,
                                                                                                                  len)
// colorma = showrib ? color.black: na
// pm1 = plot(ma1, color=color.black, title="MA")
// pm2 = plot(ma2, color=color.black, title="MA")

p1 = plot(ma1)
p2 = plot(ma2)
col = ma1 > ma2 ? color.lime: color.red
fill(p1, p2, color=col, transp=50)
// fill(pm1, pm2, color=col, transp=60)
