package minicpbp.engine.constraints;

import minicpbp.engine.core.AbstractConstraint;
import minicpbp.engine.core.IntVar;

public class Equal extends AbstractConstraint {
    private final IntVar x, y;


    /**
     * Creates a constraint such
     * that {@code x = y}
     *
     * @param x the left member
     * @param y the right memer
     * @see minicpbp.cp.Factory#equal(IntVar, IntVar)
     */
    public Equal(IntVar x, IntVar y) { // x == y
        super(x.getSolver(), new IntVar[]{x,y});
        setName("Equal");
        this.x = x;
        this.y = y;
    }

    @Override
    public void post() {
        if (y.isBound())
            x.assign(y.min());
        else if (x.isBound())
            y.assign(x.min());
        else {
            boundsIntersect();
            int[] domVal = new int[Math.max(x.size(), y.size())];
            pruneEquals(y, x, domVal);
            pruneEquals(x, y, domVal);
            x.whenDomainChange(() -> {
                boundsIntersect();
                pruneEquals(x, y, domVal);
            });
            y.whenDomainChange(() -> {
                boundsIntersect();
                pruneEquals(y, x, domVal);
            });
        }
    }

    // dom consistent filtering in the direction from -> to
    // every value of to has a support in from
    private void pruneEquals(IntVar from, IntVar to, int[] domVal) {
        // dump the domain of to into domVal
        int nVal = to.fillArray(domVal);
        for (int k = 0; k < nVal; k++)
            if (!from.contains(domVal[k]))
                to.remove(domVal[k]);
    }

    // make sure bound of variables are the same
    private void boundsIntersect() {
        int newMin = Math.max(x.min(), y.min());
        int newMax = Math.min(x.max(), y.max());
        x.removeBelow(newMin);
        x.removeAbove(newMax);
        y.removeBelow(newMin);
        y.removeAbove(newMax);
    }

    @Override
    public void updateBelief() {
        // Treatment of x
        int nVal = x.fillArray(domainValues);
        for (int k = 0; k < nVal; k++) {
            int vx = domainValues[k];
            if (y.contains(vx))
                setLocalBelief(0, vx, outsideBelief(1, vx));
            else
                setLocalBelief(0, vx, beliefRep.zero());
        }
        // Treatment of y
        nVal = y.fillArray(domainValues);
        for (int k = 0; k < nVal; k++) {
            int vy = domainValues[k];
            if (x.contains(vy))
                setLocalBelief(1, vy, outsideBelief(0, vy));
            else
                setLocalBelief(1, vy, beliefRep.zero());
        }
    }
}
