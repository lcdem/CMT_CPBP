package minicpbp.examples;

import minicpbp.cp.Factory;
import minicpbp.engine.core.Constraint;
import minicpbp.engine.core.IntVar;
import minicpbp.engine.core.Solver;
import minicpbp.util.exception.InconsistencyException;

import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.io.PrintStream;
import java.util.Arrays;
import java.util.Scanner;

import static minicpbp.cp.Factory.*;

public class rhythmAlldifferent {

    public static int nbVar = 128;
    public static int nbVarPerBar = 16;
    public static int nbBar = nbVar / nbVarPerBar;
    public static int nbVal = 3;
    public static int onSetToken = 2;

    public static void main(String[] args) {
        System.out.print("début");
        String filename = args[0];
        int nbSample = Integer.parseInt(args[1]);
        int idx = Integer.parseInt(args[2]);
        double oracleWeight = Double.parseDouble(args[3]);
        int groupSize = Integer.parseInt(args[4]);

        try {
            System.out.println();
            Scanner scanner = new Scanner(new FileReader("C:\\Users\\lcdem\\Downloads\\" + filename));
            redirectStdout(filename);
            System.out.print("après scanner");
            for (int j = 0; j < nbSample; j++) {
                Solver cp = Factory.makeSolver();

                IntVar[] x = new IntVar[nbVar]; // taille: 128
                for (int i = 0; i < nbVar; i++) {
                    x[i] = makeIntVar(cp, 0, nbVal-1);
                    x[i].setName("x"+"["+i+"]");
                }
                initVar(x, nbVar, nbVal, idx, scanner);

                double[] marginal = new double[nbVal]; // tableau initialisé de taille 3
                int[] v = new int[nbVal]; // v prend trois valeurs: 0, 1, 2 (tokens)
                for (int i = 0; i < nbVal; i++) {
                    marginal[i] = (x[idx].contains(i) ? x[idx].marginal(i) : 0); // marginal de i sera soit sa marginale existante soit 0
                    v[i] = i; // on remplit v => v[0] = 0, etc
                }

                IntVar[] o = new IntVar[groupSize]; // tableau initialisé de taille ex: 2
                for (int i = 0; i < groupSize; i++) {
                    o[i] = makeIntVar(cp, 0, nbVarPerBar); // o[0], o[1], o[2] => val min 0, max 16
                    o[i].setName("o"+"["+i+"]");
                }

                for (int i = 0; i < groupSize; i++) {
                    IntVar[] x_subset = Arrays.copyOfRange(x, i * nbVarPerBar, (i + 1) * nbVarPerBar); // la plage de temps sur lesquels appliquer la contrainte, donc x_sub_0 = [0, 16], x_sub_1 = [16, 32] etc
                    cp.post(Factory.among(x_subset, onSetToken, o[i])); // application de la contrainte among => dans x_subset, onset token doit arriver entre 0 et 16 fois
                }

                cp.post(Factory.allDifferentAC(o)); // contrainte

                Constraint orac = Factory.oracle(x[idx], v, marginal);
                orac.setWeight(oracleWeight);
                cp.post(orac);

                cp.fixPoint();
                cp.beliefPropa();

                for (int i = 0; i < nbVal; i++) {
                    System.out.print((x[idx].contains(i) ? x[idx].marginal(i) : 0) + " ");
                }
                System.out.println();
            }
            scanner.close();
        }
        catch (IOException e) {
            System.err.println("Error 1: " + e.getMessage()) ;
            System.exit(1) ;
        }
        catch (InconsistencyException e) {
            System.err.println("Error 2: " + "Inconsistency Exception");
            System.exit(2) ;
        }
        catch (Exception  e) {
            System.err.println("Error 3: " + e.getMessage());
            System.exit(3) ;
        }
    }

    public static void redirectStdout(String filename) {
        try {
            PrintStream fileOut = new PrintStream("minicpbp/examples/data/MusicCP/" + filename.substring(0, filename.length() - 4) + "_results.dat");
            System.setOut(fileOut);
        }
        catch(FileNotFoundException e) {
            System.err.println("Error 1: " + e.getMessage()) ;
            System.exit(1) ;
        }
    }

    public static void initVar(IntVar[] x, int nbVar, int nbVal, int idx, Scanner s){
        // set value of previously fixed vars
        for (int i = 0; i < idx; i++) {
            int token = s.nextInt();
            x[i].assign(token);
        }

        // set marginals for variable being fixed
        for (int i = 0; i < nbVal; i++) {
            double score = s.nextDouble();
            if (x[idx].contains(i)) {
                x[idx].setMarginal(i, score);
            }
        }
        x[idx].normalizeMarginals();

        // set uniform marginals for following variables
        for (int i = idx + 1; i < nbVar; i++) {
            x[i].resetMarginals();
            x[i].normalizeMarginals();
        }
    }
}
